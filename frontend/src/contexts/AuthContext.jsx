import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react'
import apiService from '../services/api.js'
import { info as logInfo, error as logError } from '../utils/logger.js'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [accessToken, setAccessToken] = useState(null)
  const [authError, setAuthError] = useState(null)

  // Initialize authentication state on app start
  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    try {
      setIsLoading(true)
      
      // Try to get stored token
      const storedToken = localStorage.getItem('accessToken')
      if (storedToken) {
        apiService.setToken(storedToken)
        setAccessToken(storedToken)
        
        // Verify token is still valid and get user data
        try {
          const userData = await apiService.getCurrentUser()
          setUser(userData)
          setIsAuthenticated(true)
          logInfo('User session restored successfully')
        } catch (error) {
          // Token is invalid, try to refresh
          logError('Stored token invalid, attempting refresh', error)
          await handleTokenRefresh()
        }
      } else {
        // No stored token - check if we have any indication of previous auth before attempting refresh
        const hasAuthHistory = localStorage.getItem('hasBeenAuthenticated') === 'true' || 
                              document.cookie.includes('refresh_token') ||
                              document.cookie.includes('session')
        
        if (hasAuthHistory) {
          try {
            await handleTokenRefresh()
          } catch (error) {
            // No valid refresh cookie, just set as unauthenticated
            logInfo('No valid refresh token available', error)
          }
        } else {
          // No indication of previous auth, skip refresh attempt to avoid 401 spam
          logInfo('No auth history found, starting unauthenticated')
        }
      }
    } catch (error) {
      logError('Auth initialization failed', error)
      await logout()
    } finally {
      setIsLoading(false)
    }
  }

  const handleTokenRefresh = async () => {
    try {
      const response = await apiService.refreshToken()
      const { access_token, user_id, email, username, email_verified, tier, is_superuser } = response
      
      setAccessToken(access_token)
      apiService.setToken(access_token)
      localStorage.setItem('accessToken', access_token)
      
      setUser({ id: user_id, email, username, email_verified, tier, is_superuser })
      setIsAuthenticated(true)
      setAuthError(null)
      
      // Mark that user has been authenticated to avoid unnecessary refresh attempts
      localStorage.setItem('hasBeenAuthenticated', 'true')
      
      logInfo('Token refreshed successfully')
    } catch (error) {
      logError('Token refresh failed', error)
      // Guard against infinite logout loops - only call logout if currently authenticated
      if (isAuthenticated) {
        await logout()
      }
    }
  }

  const login = async (credentials) => {
    try {
      setIsLoading(true)
      setAuthError(null)
      
      const response = await apiService.login(credentials)
      const { access_token, user_id, email, username, email_verified, tier, is_superuser } = response
      
      setAccessToken(access_token)
      apiService.setToken(access_token)
      localStorage.setItem('accessToken', access_token)
      
      setUser({ id: user_id, email, username, email_verified, tier, is_superuser })
      setIsAuthenticated(true)
      
      // Mark that user has been authenticated to avoid unnecessary refresh attempts
      localStorage.setItem('hasBeenAuthenticated', 'true')
      
      logInfo('User logged in successfully')
      return response
    } catch (error) {
      logError('Login failed', error)
      setAuthError(error.message || 'Login failed')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (userData) => {
    try {
      setIsLoading(true)
      setAuthError(null)
      
      const response = await apiService.register(userData)
      const { access_token, user_id, email, username, email_verified, tier, is_superuser } = response
      
      setAccessToken(access_token)
      apiService.setToken(access_token)
      localStorage.setItem('accessToken', access_token)
      
      setUser({ id: user_id, email, username, email_verified, tier, is_superuser })
      setIsAuthenticated(true)
      
      // Mark that user has been authenticated to avoid unnecessary refresh attempts  
      localStorage.setItem('hasBeenAuthenticated', 'true')
      
      logInfo('User registered successfully')
      return response
    } catch (error) {
      logError('Registration failed', error)
      setAuthError(error.message || 'Registration failed')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      setIsLoading(true)
      
      // Only call backend logout if user is currently authenticated
      if (isAuthenticated && accessToken) {
        try {
          await apiService.logout()
        } catch (error) {
          logError('Backend logout failed', error)
          // Continue with frontend logout even if backend fails
        }
      } else {
        logInfo('User already unauthenticated, skipping backend logout')
      }
      
      // Clear local state
      setUser(null)
      setIsAuthenticated(false)
      setAccessToken(null)
      setAuthError(null)
      
      // Clear stored token and auth history
      localStorage.removeItem('accessToken')
      localStorage.removeItem('hasBeenAuthenticated')
      apiService.setToken(null)
      
      logInfo('User logged out successfully')
    } catch (error) {
      logError('Logout error', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getAccessTokenSilently = async () => {
    if (!accessToken) {
      await handleTokenRefresh()
    }
    return accessToken
  }

  const updateUserProfile = async (updates) => {
    try {
      setUser(prevUser => ({ ...prevUser, ...updates }))
      logInfo('User profile updated')
    } catch (error) {
      logError('Profile update failed', error)
      throw error
    }
  }

  // Set up automatic token refresh
  useEffect(() => {
    if (!isAuthenticated || !accessToken) return

    // Refresh token 5 minutes before expiration (access token expires in 15 minutes)
    const refreshInterval = setInterval(async () => {
      try {
        await handleTokenRefresh()
      } catch (error) {
        logError('Automatic token refresh failed', error)
        await logout()
      }
    }, 10 * 60 * 1000) // Refresh every 10 minutes

    return () => clearInterval(refreshInterval)
  }, [isAuthenticated, accessToken])

  // Memoize callbacks to prevent context re-renders
  const clearError = useCallback(() => setAuthError(null), [])
  const loginWithRedirect = useCallback(() => {
    throw new Error('loginWithRedirect is not supported in production mode. Use login() instead.')
  }, [])
  
  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(() => ({
    user,
    isAuthenticated,
    isLoading,
    accessToken,
    authError,
    login,
    register,
    logout,
    getAccessTokenSilently,
    updateUserProfile,
    clearError,
    loginWithRedirect,
    isDemo: false // Production mode
  }), [
    user, 
    isAuthenticated, 
    isLoading, 
    accessToken, 
    authError,
    login,
    register,
    logout,
    getAccessTokenSilently,
    updateUserProfile,
    clearError,
    loginWithRedirect
  ])

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}