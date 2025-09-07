import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
import { info as logInfo, error as logError } from '../utils/logger.js'

const AdminAuthContext = createContext()

export const useAdminAuth = () => {
  const context = useContext(AdminAuthContext)
  if (!context) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider')
  }
  return context
}

/**
 * Secure Admin API Service
 * 
 * SECURITY IMPROVEMENTS:
 * - Memory-only token storage (no localStorage)
 * - HTTP-only cookie support for admin refresh tokens
 * - Automatic token refresh on 401 responses
 */
class SecureAdminApiService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    this.token = null
    this.refreshPromise = null
  }

  setToken(token) {
    this.token = token
  }

  async request(endpoint, options = {}) {
    return await this._requestWithRetry(endpoint, options, false)
  }

  async _requestWithRetry(endpoint, options = {}, isRetry = false) {
    const url = `${this.baseURL}${endpoint}`
    
    const config = {
      credentials: 'include', // For HTTP-only cookies
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    }

    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`
    }

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body)
    }

    try {
      const response = await fetch(url, config)
      
      // Handle 401 Unauthorized - attempt token refresh for admin
      if (response.status === 401 && !isRetry && endpoint !== '/api/admin/auth/refresh') {
        logInfo('Admin access token expired, attempting refresh')
        
        try {
          await this._refreshAdminToken()
          logInfo('Admin token refresh successful, retrying original request')
          
          // Retry original request with new token
          return await this._requestWithRetry(endpoint, options, true)
        } catch (refreshError) {
          logError('Admin token refresh failed', refreshError)
          throw new Error('Admin authentication session expired')
        }
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }
      
      return await response.text()
    } catch (error) {
      logError(`Admin API request failed: ${endpoint}`, error)
      throw error
    }
  }

  async _refreshAdminToken() {
    // Prevent concurrent refresh attempts
    if (this.refreshPromise) {
      return await this.refreshPromise
    }

    this.refreshPromise = this._performAdminTokenRefresh()
    
    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.refreshPromise = null
    }
  }

  async _performAdminTokenRefresh() {
    try {
      const response = await fetch(`${this.baseURL}/api/admin/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Admin token refresh failed')
      }

      const data = await response.json()
      this.token = data.access_token
      
      logInfo('Admin access token refreshed successfully')
      return data
      
    } catch (error) {
      logError('Admin token refresh failed', error)
      this.token = null
      throw error
    }
  }

  async login(credentials) {
    return this.request('/api/admin/auth/login', {
      method: 'POST',
      body: credentials,
    })
  }

  async logout() {
    const result = await this.request('/api/admin/auth/logout', {
      method: 'POST',
    })
    this.token = null
    return result
  }

  async getCurrentUser() {
    return this.request('/api/admin/auth/me')
  }

  async getUsers(page = 1, limit = 20) {
    return this.request(`/api/admin/users?page=${page}&limit=${limit}`)
  }

  async getUserById(userId) {
    return this.request(`/api/admin/users/${userId}`)
  }

  async updateUser(userId, data) {
    return this.request(`/api/admin/users/${userId}`, {
      method: 'PUT',
      body: data,
    })
  }

  async deleteUser(userId) {
    return this.request(`/api/admin/users/${userId}`, {
      method: 'DELETE',
    })
  }

  async getSystemStats() {
    return this.request('/api/admin/stats')
  }

  async getAuditLogs(page = 1, limit = 20) {
    return this.request(`/api/admin/audit?page=${page}&limit=${limit}`)
  }
}

const adminApiService = new SecureAdminApiService()

export const AdminAuthProvider = ({ children }) => {
  const [adminUser, setAdminUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  // Use ref for access token (memory only)
  const accessTokenRef = useRef(null)
  const refreshTimeoutRef = useRef(null)

  useEffect(() => {
    initializeAdminAuth()
  }, [])

  const initializeAdminAuth = async () => {
    try {
      setIsLoading(true)
      
      // Try to refresh token (using HTTP-only cookie)
      logInfo('Initializing admin auth - checking for valid refresh token')
      await handleTokenRefresh()
      
    } catch (error) {
      logInfo('No valid admin authentication session found', error)
      clearAuthState()
    } finally {
      setIsLoading(false)
    }
  }

  const handleTokenRefresh = async () => {
    try {
      const response = await adminApiService._refreshAdminToken()
      const { access_token, user_id, email, username, is_superuser } = response
      
      accessTokenRef.current = access_token
      adminApiService.setToken(access_token)
      
      setAdminUser({ id: user_id, email, username, is_superuser })
      setIsAuthenticated(true)
      setAuthError(null)
      
      scheduleTokenRefresh()
      logInfo('Admin token refreshed successfully')
      
    } catch (error) {
      logError('Admin token refresh failed', error)
      clearAuthState()
      throw error
    }
  }

  const scheduleTokenRefresh = () => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
    }

    // Refresh token 5 minutes before expiry (admin tokens expire in 15 minutes)
    refreshTimeoutRef.current = setTimeout(async () => {
      try {
        await handleTokenRefresh()
      } catch (error) {
        logError('Scheduled admin token refresh failed', error)
        await logout()
      }
    }, 10 * 60 * 1000) // 10 minutes
  }

  const clearAuthState = () => {
    accessTokenRef.current = null
    adminApiService.setToken(null)
    
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
      refreshTimeoutRef.current = null
    }
    
    setAdminUser(null)
    setIsAuthenticated(false)
    setAuthError(null)
    
    // Clear legacy localStorage
    localStorage.removeItem('adminAccessToken')
    
    logInfo('Admin auth state cleared')
  }

  const login = async (credentials) => {
    try {
      setIsLoading(true)
      setAuthError(null)
      
      const response = await adminApiService.login(credentials)
      const { access_token, user_id, email, username, is_superuser } = response
      
      accessTokenRef.current = access_token
      adminApiService.setToken(access_token)
      
      setAdminUser({ id: user_id, email, username, is_superuser })
      setIsAuthenticated(true)
      
      scheduleTokenRefresh()
      logInfo('Admin logged in successfully')
      
      return response
    } catch (error) {
      logError('Admin login failed', error)
      setAuthError(error.message || 'Login failed')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      setIsLoading(true)
      
      if (isAuthenticated && accessTokenRef.current) {
        try {
          await adminApiService.logout()
          logInfo('Admin backend logout successful')
        } catch (error) {
          logError('Admin backend logout failed', error)
        }
      }
      
      clearAuthState()
      logInfo('Admin logged out successfully')
      
    } catch (error) {
      logError('Admin logout error', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getAccessTokenSilently = async () => {
    if (accessTokenRef.current) {
      return accessTokenRef.current
    }
    
    try {
      await handleTokenRefresh()
      return accessTokenRef.current
    } catch (error) {
      logError('Silent admin token retrieval failed', error)
      await logout()
      throw new Error('Admin authentication session expired')
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current)
      }
    }
  }, [])

  const value = {
    adminUser,
    isAuthenticated,
    isLoading,
    authError,
    login,
    logout,
    getAccessTokenSilently,
    clearError: () => setAuthError(null),
    apiService: adminApiService,
    isSecureAuth: true,
    tokenStorageType: 'memory-only'
  }

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  )
}