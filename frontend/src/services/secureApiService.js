import { error as logError, info as logInfo } from '../utils/logger.js'
import errorReporter from '../utils/errorReporter.jsx'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Enhanced API Service with Secure Token Management
 * 
 * SECURITY IMPROVEMENTS:
 * - Automatic token refresh on 401 responses
 * - No localStorage token storage (XSS protection)
 * - Memory-only access token management
 * - HTTP-only cookie refresh tokens
 * - Comprehensive error handling with retry logic
 */
class SecureApiService {
  constructor() {
    this.baseURL = API_BASE_URL
    this.token = null
    this.csrfToken = null
    this.refreshPromise = null // Prevent concurrent refreshes
    this.tokenRefreshCallback = null // Callback to notify auth context of token updates
    this._initializeCSRF()
  }

  /**
   * Set callback for token refresh notifications
   * Used by AuthContext to update token state
   */
  setTokenRefreshCallback(callback) {
    this.tokenRefreshCallback = callback
  }

  /**
   * Set access token (memory only - never localStorage)
   */
  setToken(token) {
    this.token = token
  }

  setCSRFToken(token) {
    this.csrfToken = token
  }

  // Initialize CSRF token from cookie or fetch from server
  async _initializeCSRF() {
    try {
      // Try to get CSRF token from cookie first
      const cookieToken = this._getCSRFTokenFromCookie()
      if (cookieToken) {
        this.csrfToken = cookieToken
        return
      }

      // If no cookie token, fetch from server
      await this.fetchCSRFToken()
    } catch (error) {
      console.warn('Failed to initialize CSRF token:', error)
    }
  }

  // Get CSRF token from cookie
  _getCSRFTokenFromCookie() {
    if (typeof document === 'undefined') return null

    const cookies = document.cookie.split(';')
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=')
      if (name === 'csrftoken') {
        return decodeURIComponent(value)
      }
    }
    return null
  }

  // Fetch CSRF token from server
  async fetchCSRFToken() {
    try {
      const response = await fetch(`${this.baseURL}/api/auth/csrf-token`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        this.csrfToken = data.csrf_token

        // Also check for CSRF token in response headers
        const headerToken = response.headers.get('X-CSRF-Token')
        if (headerToken) {
          this.csrfToken = headerToken
        }
      }
    } catch (error) {
      console.warn('Failed to fetch CSRF token:', error)
    }
  }

  /**
   * Enhanced request method with automatic token refresh
   */
  async request(endpoint, options = {}) {
    return await this._requestWithRetry(endpoint, options, false)
  }

  async _requestWithRetry(endpoint, options = {}, isRetry = false) {
    const url = `${this.baseURL}${endpoint}`

    const config = {
      credentials: 'include', // Essential for HTTP-only cookies
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    }

    // Add access token if available (memory only)
    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`
    }

    // Add CSRF token for state-changing requests
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method?.toUpperCase())) {
      if (!this.csrfToken) {
        this.csrfToken = this._getCSRFTokenFromCookie()
      }

      if (this.csrfToken) {
        config.headers['X-CSRF-Token'] = this.csrfToken
      } else {
        console.warn('No CSRF token available for state-changing request:', endpoint)
      }
    }

    // Handle FormData - don't set Content-Type, let browser set it with boundary
    if (config.body instanceof FormData) {
      delete config.headers['Content-Type']
    } else if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body)
    }

    try {
      // Add timeout to prevent hanging requests
      const controller = new AbortController()
      const timeoutMs = Number(import.meta.env.VITE_FETCH_TIMEOUT_MS || 15000)
      const timeout = setTimeout(() => controller.abort(), timeoutMs)

      let response
      try {
        response = await fetch(url, {
          ...config,
          signal: controller.signal,
        })
        clearTimeout(timeout)
      } catch (fetchError) {
        clearTimeout(timeout)
        throw fetchError
      }

      // Update CSRF token from response headers if present
      const newCSRFToken = response.headers.get('X-CSRF-Token')
      if (newCSRFToken && newCSRFToken !== this.csrfToken) {
        this.csrfToken = newCSRFToken
      }

      // Handle successful responses
      if (response.ok) {
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          return await response.json()
        }
        return await response.text()
      }

      // Handle error responses
      const errorData = await response.json().catch(() => ({}))

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && !isRetry && endpoint !== '/api/auth/refresh') {
        logInfo('Access token expired, attempting refresh')
        
        try {
          // Attempt token refresh using HTTP-only cookie
          await this._refreshAccessToken()
          logInfo('Token refresh successful, retrying original request')
          
          // Retry original request with new token
          return await this._requestWithRetry(endpoint, options, true)
        } catch (refreshError) {
          logError('Token refresh failed', refreshError)
          
          // Notify auth context of authentication failure
          if (this.tokenRefreshCallback) {
            this.tokenRefreshCallback(null) // Clear token
          }
          
          throw new Error('Authentication session expired')
        }
      }

      // Handle CSRF errors
      if (response.status === 403 && errorData.code === 'CSRF_FAILURE') {
        console.warn('CSRF token invalid, attempting to refresh')
        await this.fetchCSRFToken()

        // Retry the request once with new CSRF token
        if (options.retryCSRF !== false) {
          return this._requestWithRetry(endpoint, { ...options, retryCSRF: false }, isRetry)
        }
      }

      // Report API errors
      errorReporter.logNetworkError(
        endpoint,
        config.method || 'GET',
        response.status,
        errorData.detail || `HTTP error! status: ${response.status}`
      )

      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)

    } catch (error) {
      logError(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  /**
   * Refresh access token using HTTP-only refresh token cookie
   */
  async _refreshAccessToken() {
    // Prevent concurrent refresh attempts
    if (this.refreshPromise) {
      logInfo('Token refresh already in progress, waiting...')
      return await this.refreshPromise
    }

    this.refreshPromise = this._performTokenRefresh()
    
    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.refreshPromise = null
    }
  }

  async _performTokenRefresh() {
    try {
      const response = await fetch(`${this.baseURL}/api/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // Essential for HTTP-only refresh token
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Token refresh failed')
      }

      const data = await response.json()
      
      // Update access token in memory
      this.token = data.access_token
      
      // Notify auth context of new token
      if (this.tokenRefreshCallback) {
        this.tokenRefreshCallback(data.access_token)
      }

      logInfo('Access token refreshed successfully')
      return data
      
    } catch (error) {
      logError('Token refresh failed', error)
      // Clear invalid token
      this.token = null
      throw error
    }
  }

  // Auth endpoints
  async register(userData) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: userData,
    })
  }

  async login(credentials) {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: credentials,
    })
  }

  async getCurrentUser() {
    return this.request('/api/auth/me')
  }

  async refreshToken() {
    return this.request('/api/auth/refresh', {
      method: 'POST',
    })
  }

  async logout() {
    const result = await this.request('/api/auth/logout', {
      method: 'POST',
    })
    
    // Clear token on logout
    this.token = null
    
    return result
  }

  async verifyAuth() {
    return this.request('/api/auth/verify')
  }

  async getAuthConfig() {
    return this.request('/api/auth/config')
  }

  // Email verification endpoints
  async verifyEmail(token) {
    return this.request('/api/auth/verify-email', {
      method: 'POST',
      body: { token },
    })
  }

  async resendVerification(email) {
    return this.request('/api/auth/resend-verification', {
      method: 'POST',
      body: { email },
    })
  }

  // Password reset endpoints
  async forgotPassword(email) {
    return this.request('/api/auth/forgot-password', {
      method: 'POST',
      body: { email },
    })
  }

  async resetPassword(token, new_password) {
    return this.request('/api/auth/reset-password', {
      method: 'POST',
      body: { token, new_password },
    })
  }

  // Memory endpoints (v2)
  async storeMemory(content, metadata) {
    return this.request('/api/memory/store', {
      method: 'POST',
      body: { content, metadata },
    })
  }

  async searchMemory(query, limit = 5) {
    const response = await this.request('/api/memory/search', {
      method: 'POST',
      body: { query, top_k: limit },
    })
    return response.results || []
  }

  async getAllMemory(page = 1, limit = 20) {
    const response = await this.request(`/api/memory/?page=${page}&limit=${limit}`)
    return response.content || []
  }

  async getMemoryById(contentId) {
    return this.request(`/api/memory/${contentId}`)
  }

  async deleteMemory(contentId) {
    return this.request(`/api/memory/${contentId}`, {
      method: 'DELETE',
    })
  }

  async getMemoryStats() {
    return this.request('/api/memory/stats')
  }

  // Content creation endpoints
  async generateContent(data) {
    return this.request('/api/content/generate', {
      method: 'POST',
      body: data,
    })
  }

  async generateImage(data) {
    return this.request('/api/content/generate-image', {
      method: 'POST',
      body: data,
    })
  }

  async getContent(contentId) {
    return this.request(`/api/content/${contentId}`)
  }

  async updateContent(contentId, data) {
    return this.request(`/api/content/${contentId}`, {
      method: 'PUT',
      body: data,
    })
  }

  async deleteContent(contentId) {
    return this.request(`/api/content/${contentId}`, {
      method: 'DELETE',
    })
  }

  async listContent(page = 1, limit = 20) {
    return this.request(`/api/content?page=${page}&limit=${limit}`)
  }

  // Post management endpoints
  async createPost(data) {
    return this.request('/api/posts/', {
      method: 'POST',
      body: data,
    })
  }

  async getPosts(page = 1, limit = 20) {
    return this.request(`/api/posts/?page=${page}&limit=${limit}`)
  }

  async getPost(postId) {
    return this.request(`/api/posts/${postId}`)
  }

  async updatePost(postId, data) {
    return this.request(`/api/posts/${postId}`, {
      method: 'PUT',
      body: data,
    })
  }

  async deletePost(postId) {
    return this.request(`/api/posts/${postId}`, {
      method: 'DELETE',
    })
  }

  async publishPost(postId, platforms) {
    return this.request(`/api/posts/${postId}/publish`, {
      method: 'POST',
      body: { platforms },
    })
  }

  // Analytics endpoints
  async getAnalytics(timeframe = '7d') {
    return this.request(`/api/analytics?timeframe=${timeframe}`)
  }

  async getContentAnalytics(contentId) {
    return this.request(`/api/analytics/content/${contentId}`)
  }

  // Partner OAuth endpoints
  async getPartnerOAuthConfig() {
    return this.request('/api/partner-oauth/config')
  }

  async initiatePartnerOAuth(platform) {
    return this.request('/api/partner-oauth/initiate', {
      method: 'POST',
      body: { platform },
    })
  }

  async completePartnerOAuth(code, state) {
    return this.request('/api/partner-oauth/callback', {
      method: 'POST',
      body: { code, state },
    })
  }

  async getConnectedAccounts() {
    return this.request('/api/partner-oauth/connections')
  }

  async disconnectAccount(connectionId) {
    return this.request(`/api/partner-oauth/connections/${connectionId}`, {
      method: 'DELETE',
    })
  }

  // Settings endpoints
  async getUserSettings() {
    return this.request('/api/settings')
  }

  async updateUserSettings(settings) {
    return this.request('/api/settings', {
      method: 'PUT',
      body: settings,
    })
  }

  // Billing endpoints
  async getBillingInfo() {
    return this.request('/api/billing')
  }

  async createSubscription(planId) {
    return this.request('/api/billing/subscribe', {
      method: 'POST',
      body: { plan_id: planId },
    })
  }

  async cancelSubscription() {
    return this.request('/api/billing/cancel', {
      method: 'POST',
    })
  }

  async getInvoices() {
    return this.request('/api/billing/invoices')
  }

  // Admin endpoints (if user has admin privileges)
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

  // PW-FE-ADD-001: Settings API endpoints
  async getSettings() {
    return this.request('/api/v1/settings')
  }

  async updateSettings(settings) {
    return this.request('/api/v1/settings', {
      method: 'PUT',
      body: settings,
    })
  }

  async getPricingSettings() {
    return this.request('/api/v1/settings/pricing')
  }

  async updatePricingSettings(settings) {
    return this.request('/api/v1/settings/pricing', {
      method: 'PUT',
      body: settings,
    })
  }

  async getWeatherSettings() {
    return this.request('/api/v1/settings/weather')
  }

  async updateWeatherSettings(settings) {
    return this.request('/api/v1/settings/weather', {
      method: 'PUT',
      body: settings,
    })
  }

  async getBookingSettings() {
    return this.request('/api/v1/settings/booking')
  }

  async updateBookingSettings(settings) {
    return this.request('/api/v1/settings/booking', {
      method: 'PUT',
      body: settings,
    })
  }
}

// Create and export singleton instance
const secureApiService = new SecureApiService()
export default secureApiService