import React, { createContext, useContext, useState, useEffect } from 'react'
import { info as logInfo, error as logError } from '../utils/logger.js'

const AdminAuthContext = createContext()

export const useAdminAuth = () => {
  const context = useContext(AdminAuthContext)
  if (!context) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider')
  }
  return context
}

class AdminApiService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    this.token = null
  }

  setToken(token) {
    this.token = token
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    
    const config = {
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

  // Admin Authentication
  async adminLogin(credentials) {
    return this.request('/api/admin/auth/login', {
      method: 'POST',
      body: credentials
    })
  }

  async adminLogout() {
    return this.request('/api/admin/auth/logout', {
      method: 'POST'
    })
  }

  async getAdminProfile() {
    return this.request('/api/admin/auth/me')
  }

  // Dashboard
  async getDashboard() {
    return this.request('/api/admin/dashboard')
  }

  // User Management
  async getUsers(params = {}) {
    const searchParams = new URLSearchParams(params)
    return this.request(`/api/admin/users?${searchParams}`)
  }

  async getUserDetails(userId) {
    return this.request(`/api/admin/users/${userId}`)
  }

  async updateUserManagement(userId, data) {
    return this.request(`/api/admin/users/${userId}/management`, {
      method: 'PUT',
      body: data
    })
  }

  async generateApiKey(userId) {
    return this.request(`/api/admin/users/${userId}/api-key`, {
      method: 'POST'
    })
  }

  async revokeApiKey(userId, reason = 'Admin revocation') {
    return this.request(`/api/admin/users/${userId}/api-key`, {
      method: 'DELETE',
      body: { reason }
    })
  }

  // Admin Users Management
  async createAdminUser(data) {
    return this.request('/api/admin/admin-users', {
      method: 'POST',
      body: data
    })
  }

  async getAdminUsers() {
    return this.request('/api/admin/admin-users')
  }

  // System Settings
  async getSystemSettings() {
    return this.request('/api/admin/settings')
  }

  async updateSystemSetting(key, data) {
    return this.request(`/api/admin/settings/${key}`, {
      method: 'PUT',
      body: data
    })
  }

  // Audit Logs
  async getAuditLogs(params = {}) {
    const searchParams = new URLSearchParams(params)
    return this.request(`/api/admin/audit-logs?${searchParams}`)
  }
}

const adminApiService = new AdminApiService()

export const AdminAuthProvider = ({ children }) => {
  const [adminUser, setAdminUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [accessToken, setAccessToken] = useState(null)
  const [authError, setAuthError] = useState(null)

  // Initialize admin authentication state on app start
  useEffect(() => {
    initializeAdminAuth()
  }, [])

  const initializeAdminAuth = async () => {
    try {
      setIsLoading(true)
      
      // Try to get stored admin token
      const storedToken = localStorage.getItem('adminAccessToken')
      if (storedToken) {
        adminApiService.setToken(storedToken)
        setAccessToken(storedToken)
        
        // Verify token is still valid and get admin data
        try {
          const adminData = await adminApiService.getAdminProfile()
          setAdminUser(adminData)
          setIsAuthenticated(true)
          logInfo('Admin session restored successfully')
        } catch (error) {
          // Token is invalid, clear it
          logError('Stored admin token invalid', error)
          await adminLogout()
        }
      }
    } catch (error) {
      logError('Admin auth initialization failed', error)
      await adminLogout()
    } finally {
      setIsLoading(false)
    }
  }

  const adminLogin = async (credentials) => {
    try {
      setIsLoading(true)
      setAuthError(null)
      
      const response = await adminApiService.adminLogin(credentials)
      const { access_token, admin_user } = response
      
      setAccessToken(access_token)
      adminApiService.setToken(access_token)
      localStorage.setItem('adminAccessToken', access_token)
      
      setAdminUser(admin_user)
      setIsAuthenticated(true)
      
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

  const adminLogout = async () => {
    try {
      setIsLoading(true)
      
      // Call backend logout
      try {
        await adminApiService.adminLogout()
      } catch (error) {
        logError('Backend admin logout failed', error)
        // Continue with frontend logout even if backend fails
      }
      
      // Clear local state
      setAdminUser(null)
      setIsAuthenticated(false)
      setAccessToken(null)
      setAuthError(null)
      
      // Clear stored token
      localStorage.removeItem('adminAccessToken')
      adminApiService.setToken(null)
      
      logInfo('Admin logged out successfully')
    } catch (error) {
      logError('Admin logout error', error)
    } finally {
      setIsLoading(false)
    }
  }

  const updateAdminProfile = (updates) => {
    setAdminUser(prevUser => ({ ...prevUser, ...updates }))
  }

  const clearError = () => setAuthError(null)

  // Set up token refresh (admin tokens have shorter lifespan)
  useEffect(() => {
    if (!isAuthenticated || !accessToken) return

    // Check token every 25 minutes (tokens expire in 30 minutes)
    const checkInterval = setInterval(async () => {
      try {
        await adminApiService.getAdminProfile()
      } catch (error) {
        logError('Admin token validation failed', error)
        await adminLogout()
      }
    }, 25 * 60 * 1000) // 25 minutes

    return () => clearInterval(checkInterval)
  }, [isAuthenticated, accessToken])

  const contextValue = {
    adminUser,
    isAuthenticated,
    isLoading,
    accessToken,
    authError,
    adminLogin,
    adminLogout,
    updateAdminProfile,
    clearError,
    // API service for admin components to use
    adminApi: adminApiService
  }

  return (
    <AdminAuthContext.Provider value={contextValue}>
      {children}
    </AdminAuthContext.Provider>
  )
}