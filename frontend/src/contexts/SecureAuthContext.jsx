import React, { createContext, useContext, useState, useEffect, useMemo, useCallback, useRef } from 'react'
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

/**
 * Secure Authentication Provider
 * 
 * SECURITY IMPROVEMENTS:
 * - Access tokens are NEVER stored in localStorage (XSS protection)
 * - Refresh tokens are stored in HTTP-only cookies (not accessible to JS)
 * - Access tokens are kept in memory only during session
 * - Automatic token refresh without client-side storage
 * - Session expiry on browser close (no persistent access tokens)
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState(null)
  
  // Store access token in memory only (not localStorage)
  const accessTokenRef = useRef(null)
  const tokenRefreshInProgress = useRef(false)
  const refreshTokenTimeoutRef = useRef(null)

  // Initialize authentication state on app start
  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    try {
      setIsLoading(true)
      
      // Check if we have a refresh token cookie by attempting token refresh
      // No stored access token to check - security improvement
      logInfo('Initializing auth - checking for valid refresh token cookie')
      
      await handleTokenRefresh()
      
    } catch (error) {
      // No valid refresh cookie or error occurred
      logInfo('No valid authentication session found', error)
      await clearAuthState()
    } finally {
      setIsLoading(false)
    }
  }

  const handleTokenRefresh = async () => {
    // Prevent concurrent refresh attempts
    if (tokenRefreshInProgress.current) {
      logInfo('Token refresh already in progress, waiting...')
      // Wait for ongoing refresh to complete
      return new Promise((resolve, reject) => {
        const checkRefresh = setInterval(() => {
          if (!tokenRefreshInProgress.current) {
            clearInterval(checkRefresh)
            if (accessTokenRef.current) {
              resolve(accessTokenRef.current)
            } else {
              reject(new Error('Token refresh failed'))
            }
          }
        }, 100)
        
        // Timeout after 10 seconds
        setTimeout(() => {
          clearInterval(checkRefresh)
          reject(new Error('Token refresh timeout'))
        }, 10000)
      })
    }

    tokenRefreshInProgress.current = true

    try {
      const response = await apiService.refreshToken()
      const { access_token, user_id, email, username, email_verified, tier, is_superuser } = response
      
      // Store access token in memory only (NEVER in localStorage)
      accessTokenRef.current = access_token
      apiService.setToken(access_token)
      
      setUser({ id: user_id, email, username, email_verified, tier, is_superuser })
      setIsAuthenticated(true)
      setAuthError(null)
      
      // Schedule next token refresh (5 minutes before expiration)
      scheduleTokenRefresh()
      
      logInfo('Token refreshed successfully')
      return access_token
      
    } catch (error) {
      logError('Token refresh failed', error)
      await clearAuthState()
      throw error
    } finally {
      tokenRefreshInProgress.current = false
    }
  }

  const scheduleTokenRefresh = () => {
    // Clear existing refresh timeout
    if (refreshTokenTimeoutRef.current) {
      clearTimeout(refreshTokenTimeoutRef.current)
    }

    // Schedule refresh 5 minutes before token expiry (access token expires in 15 minutes)
    refreshTokenTimeoutRef.current = setTimeout(async () => {
      try {
        await handleTokenRefresh()
      } catch (error) {
        logError('Scheduled token refresh failed', error)
        await logout()
      }
    }, 10 * 60 * 1000) // Refresh after 10 minutes (5 min buffer)
  }

  const login = async (credentials) => {
    try {
      setIsLoading(true)
      setAuthError(null)
      
      const response = await apiService.login(credentials)
      const { access_token, user_id, email, username, email_verified, tier, is_superuser } = response
      
      // Store access token in memory only (NEVER in localStorage)
      accessTokenRef.current = access_token
      apiService.setToken(access_token)
      
      setUser({ id: user_id, email, username, email_verified, tier, is_superuser })
      setIsAuthenticated(true)
      
      // Schedule automatic token refresh
      scheduleTokenRefresh()
      
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
      
      // Store access token in memory only (NEVER in localStorage)
      accessTokenRef.current = access_token
      apiService.setToken(access_token)
      
      setUser({ id: user_id, email, username, email_verified, tier, is_superuser })
      setIsAuthenticated(true)
      
      // Schedule automatic token refresh
      scheduleTokenRefresh()
      
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

  const clearAuthState = async () => {
    // Clear memory-stored access token
    accessTokenRef.current = null
    apiService.setToken(null)
    
    // Clear refresh timeout
    if (refreshTokenTimeoutRef.current) {
      clearTimeout(refreshTokenTimeoutRef.current)
      refreshTokenTimeoutRef.current = null
    }
    
    // Clear auth state
    setUser(null)
    setIsAuthenticated(false)
    setAuthError(null)
    
    // Clear any localStorage auth history (backward compatibility cleanup)
    localStorage.removeItem('accessToken')
    localStorage.removeItem('hasBeenAuthenticated')
    
    logInfo('Auth state cleared')
  }

  const logout = async () => {
    try {
      setIsLoading(true)
      
      // Call backend logout if authenticated (will clear HTTP-only refresh token cookie)
      if (isAuthenticated && accessTokenRef.current) {
        try {
          await apiService.logout()
          logInfo('Backend logout successful')
        } catch (error) {
          logError('Backend logout failed', error)
          // Continue with frontend logout even if backend fails
        }
      }
      
      await clearAuthState()
      logInfo('User logged out successfully')
      
    } catch (error) {
      logError('Logout error', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getAccessTokenSilently = async () => {
    // If we have a valid access token in memory, return it
    if (accessTokenRef.current) {
      return accessTokenRef.current
    }
    
    // No access token - attempt refresh
    try {
      const token = await handleTokenRefresh()
      return token
    } catch (error) {
      logError('Silent token retrieval failed', error)
      // Logout user if we can't get a valid token
      await logout()
      throw new Error('Authentication session expired')
    }
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

  // Enhanced token refresh with retry logic
  const refreshTokenWithRetry = async (maxRetries = 3) => {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await handleTokenRefresh()
      } catch (error) {
        logError(`Token refresh attempt ${attempt} failed`, error)
        
        if (attempt === maxRetries) {
          throw error
        }
        
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt - 1)))
      }
    }
  }

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      if (refreshTokenTimeoutRef.current) {
        clearTimeout(refreshTokenTimeoutRef.current)
      }
    }
  }, [])

  // Memoize callbacks to prevent context re-renders
  const clearError = useCallback(() => setAuthError(null), [])
  const loginWithRedirect = useCallback(() => {
    throw new Error('loginWithRedirect is not supported in production mode. Use login() instead.')
  }, [])
  
  // Enhanced context value with security improvements
  const contextValue = useMemo(() => ({
    user,
    isAuthenticated,
    isLoading,
    authError,
    login,
    register,
    logout,
    getAccessTokenSilently,
    updateUserProfile,
    clearError,
    loginWithRedirect,
    isDemo: false, // Production mode
    // Security metadata
    tokenStorageType: 'memory-only', // Indicates secure token storage
    hasRefreshCapability: true,
    isSecureAuth: true
  }), [
    user, 
    isAuthenticated, 
    isLoading, 
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