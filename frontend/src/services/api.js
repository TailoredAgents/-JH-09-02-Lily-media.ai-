import { error as logError } from '../utils/logger.js'
import errorReporter from '../utils/errorReporter.jsx'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL
    this.token = null
  }

  setToken(token) {
    this.token = token
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    
    const config = {
      credentials: 'include', // Send cookies/credentials for CORS
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    }

    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`
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
      
      try {
        const response = await fetch(url, { 
          ...config, 
          signal: controller.signal 
        })
        clearTimeout(timeout)
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          
          // Report API errors
          errorReporter.logNetworkError(
            endpoint,
            config.method || 'GET',
            response.status,
            errorData.detail || `HTTP error! status: ${response.status}`
          )
          
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
        }

        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          return await response.json()
        }
        
        return await response.text()
      } catch (fetchError) {
        clearTimeout(timeout)
        throw fetchError
      }
    } catch (error) {
      logError(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Auth endpoints
  async register(userData) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: userData
    })
  }

  async login(credentials) {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: credentials
    })
  }

  async getCurrentUser() {
    return this.request('/api/auth/me')
  }

  async refreshToken() {
    return this.request('/api/auth/refresh', {
      method: 'POST'
    })
  }

  async logout() {
    return this.request('/api/auth/logout', {
      method: 'POST'
    })
  }

  async verifyAuth() {
    return this.request('/api/auth/verify')
  }

  async getAuthConfig() {
    return this.request('/api/auth/config')
  }

  // Memory endpoints (v2)
  async storeMemory(content, metadata) {
    return this.request('/api/memory/store', {
      method: 'POST',
      body: { content, metadata }
    })
  }

  async searchMemory(query, limit = 5) {
    const response = await this.request('/api/memory/search', {
      method: 'POST',
      body: { query, top_k: limit }
    })
    // Extract results array from response object
    return response.results || []
  }

  async getAllMemory(page = 1, limit = 20) {
    const response = await this.request(`/api/memory/?page=${page}&limit=${limit}`)
    // Extract content array from response object
    return response.content || []
  }

  async getMemoryById(contentId) {
    return this.request(`/api/memory/${contentId}`)
  }

  async updateMemory(contentId, data) {
    return this.request(`/api/memory/${contentId}`, {
      method: 'PUT',
      body: data
    })
  }

  async deleteMemory(contentId) {
    return this.request(`/api/memory/${contentId}`, {
      method: 'DELETE'
    })
  }

  async getMemoryAnalytics() {
    return this.request('/api/memory/analytics')
  }

  async getPopularTags() {
    return this.request('/api/memory/tags/popular')
  }

  // Vector Memory endpoints
  async storeVector(content, embedding, metadata) {
    return this.request('/api/memory/vector/store', {
      method: 'POST',
      body: { content, embedding, metadata }
    })
  }

  async searchVector(query, limit = 5, threshold = 0.8) {
    return this.request('/api/memory/vector/search', {
      method: 'POST',
      body: { query, limit, threshold }
    })
  }

  async getHighPerformingContent() {
    return this.request('/api/memory/vector/high-performing')
  }

  async getRepurposingCandidates() {
    return this.request('/api/memory/vector/repurposing-candidates')
  }

  async analyzeContentPatterns() {
    return this.request('/api/memory/vector/patterns')
  }

  async getVectorStats() {
    return this.request('/api/memory/vector/stats')
  }

  async syncVectorStore() {
    return this.request('/api/memory/vector/sync', {
      method: 'POST'
    })
  }

  async getContentByType(memoryType) {
    return this.request(`/api/memory/vector/by-type/${memoryType}`)
  }

  // Goals endpoints (v2)
  async createGoal(goalData) {
    return this.request('/api/goals/', {
      method: 'POST',
      body: goalData
    })
  }

  async getGoals() {
    return this.request('/api/goals/')
  }

  async getGoal(goalId) {
    return this.request(`/api/goals/${goalId}`)
  }

  async updateGoal(goalId, goalData) {
    return this.request(`/api/goals/${goalId}`, {
      method: 'PUT',
      body: goalData
    })
  }

  async updateGoalProgress(goalId, progressData) {
    return this.request(`/api/goals/${goalId}/progress`, {
      method: 'PUT',
      body: progressData
    })
  }

  async pauseGoal(goalId) {
    return this.request(`/api/goals/${goalId}/pause`, {
      method: 'PUT'
    })
  }

  async resumeGoal(goalId) {
    return this.request(`/api/goals/${goalId}/resume`, {
      method: 'PUT'
    })
  }

  async deleteGoal(goalId) {
    return this.request(`/api/goals/${goalId}`, {
      method: 'DELETE'
    })
  }

  async getGoalProgress(goalId) {
    return this.request(`/api/goals/${goalId}/progress`)
  }

  async getGoalsDashboard() {
    return this.request('/api/goals/dashboard/summary')
  }

  // Analytics endpoints (using main.py endpoints)
  async getMetrics() {
    return this.request('/api/metrics')
  }

  async getAnalytics(timeframe = '7d') {
    return this.request(`/api/analytics?timeframe=${timeframe}`)
  }

  async getPerformanceMetrics(platform = 'all') {
    return this.request(`/api/analytics/performance?platform=${platform}`)
  }

  // Content endpoints
  async createContent(contentData) {
    return this.request('/api/content/', {
      method: 'POST',
      body: contentData
    })
  }

  async getContent(page = 1, limit = 20) {
    const response = await this.request(`/api/content/?page=${page}&limit=${limit}`)
    // Extract content array from response object
    return response.content || []
  }

  async getAll(page = 1, limit = 20) {
    return this.getContent(page, limit)
  }

  async getContentItems(params = {}) {
    const searchParams = new URLSearchParams()
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        searchParams.append(key, params[key])
      }
    })
    return this.request(`/api/content/items?${searchParams}`)
  }

  async getContentById(contentId) {
    return this.request(`/api/content/${contentId}`)
  }

  async updateContent(contentId, contentData) {
    return this.request(`/api/content/${contentId}`, {
      method: 'PUT',
      body: contentData
    })
  }

  async publishContent(contentId) {
    return this.request(`/api/content/${contentId}/publish`, {
      method: 'POST'
    })
  }

  async scheduleContent(contentId, scheduleData) {
    return this.request(`/api/content/${contentId}/schedule`, {
      method: 'POST',
      body: scheduleData
    })
  }

  async deleteContent(contentId) {
    return this.request(`/api/content/${contentId}`, {
      method: 'DELETE'
    })
  }

  async getUpcomingContent() {
    const response = await this.request('/api/content/scheduled/upcoming')
    // Extract scheduled_content array from response object
    return response.scheduled_content || []
  }

  async getContentAnalytics() {
    return this.request('/api/content/analytics/summary')
  }

  async generateContent(prompt, contentType, platform = 'twitter', specificInstructions = null, companyResearchData = null) {
    return this.request('/api/content/generate', {
      method: 'POST',
      body: { 
        prompt: prompt,  // Fixed: API expects 'prompt' field, not 'topic'
        content_type: contentType,
        platform: platform,
        tone: 'professional',
        include_hashtags: true,
        specific_instructions: specificInstructions,
        company_research_data: companyResearchData
      }
    })
  }

  async uploadImage(file, description = null) {
    const formData = new FormData()
    formData.append('file', file)
    if (description) {
      formData.append('description', description)
    }

    return this.request('/api/content/upload-image', {
      method: 'POST',
      body: formData,
      headers: {} // Remove Content-Type to let browser set it with boundary
    })
  }

  async deleteUploadedImage(filename) {
    return this.request(`/api/content/upload-image/${filename}`, {
      method: 'DELETE'
    })
  }

  async generateImage(prompt, contentContext, platform, industryContext) {
    return this.request('/api/content/generate-image', {
      method: 'POST',
      body: { 
        prompt, 
        content_context: contentContext,
        platform,
        industry_context: industryContext
      }
    })
  }

  // Workflow endpoints (v2)
  async executeWorkflow(workflowData) {
    return this.request('/api/workflow/execute', {
      method: 'POST',
      body: workflowData
    })
  }

  async getWorkflowStatusSummary() {
    return this.request('/api/workflow/status/summary')
  }

  // Autonomous endpoints
  async getLatestResearch() {
    return this.request('/api/autonomous/research/latest')
  }

  async getAutonomousStatus() {
    return this.request('/api/autonomous/status')
  }

  async executeAutonomousCycle() {
    return this.request('/api/autonomous/execute-cycle', {
      method: 'POST'
    })
  }

  async researchCompany(companyName) {
    return this.request('/api/autonomous/research/company', {
      method: 'POST',
      body: { company_name: companyName }
    })
  }

  async getWorkflowExecutions() {
    return this.request('/api/workflow/')
  }

  async getWorkflowExecution(executionId) {
    return this.request(`/api/workflow/${executionId}`)
  }

  async cancelWorkflowExecution(executionId) {
    return this.request(`/api/workflow/${executionId}/cancel`, {
      method: 'POST'
    })
  }

  async executeDailyWorkflow() {
    return this.request('/api/workflow/templates/daily', {
      method: 'POST'
    })
  }

  async executeOptimizationWorkflow() {
    return this.request('/api/workflow/templates/optimization', {
      method: 'POST'
    })
  }

  // Legacy workflow endpoints (main.py)
  async getWorkflowStatus() {
    return this.request('/api/workflow/status')
  }

  async triggerWorkflow(workflowType) {
    return this.request('/api/workflow/trigger', {
      method: 'POST',
      body: { workflow_type: workflowType }
    })
  }

  // Notifications endpoints
  async getNotifications() {
    return this.request('/api/notifications/')
  }

  async getNotificationsSummary() {
    return this.request('/api/notifications/summary')
  }

  async markNotificationRead(notificationId) {
    return this.request(`/api/notifications/${notificationId}/read`, {
      method: 'PUT'
    })
  }

  async dismissNotification(notificationId) {
    return this.request(`/api/notifications/${notificationId}/dismiss`, {
      method: 'PUT'
    })
  }

  async markAllNotificationsRead() {
    return this.request('/api/notifications/mark-all-read', {
      method: 'PUT'
    })
  }

  async deleteNotification(notificationId) {
    return this.request(`/api/notifications/${notificationId}`, {
      method: 'DELETE'
    })
  }

  async checkGoalNotifications() {
    return this.request('/api/notifications/check-goals', {
      method: 'POST'
    })
  }

  async getNotificationTypes() {
    return this.request('/api/notifications/types')
  }

  // Social Platform endpoints
  async connectSocialPlatform(platform) {
    return this.request(`/api/social/connect/${platform}`)
  }

  async getSocialConnections() {
    return this.request('/api/social/connections')
  }

  async disconnectSocialPlatform(connectionId) {
    return this.request(`/api/social/connections/${connectionId}`, {
      method: 'DELETE'
    })
  }

  async validateSocialConnection(platform) {
    return this.request(`/api/social/validate/${platform}`, {
      method: 'POST'
    })
  }

  async postToSocialPlatforms(content, platforms, mediaUrls = null, scheduleFor = null) {
    return this.request('/api/social/post', {
      method: 'POST',
      body: {
        content,
        platforms,
        media_urls: mediaUrls,
        schedule_for: scheduleFor
      }
    })
  }

  async getSocialPosts(platform = null, limit = 20, offset = 0) {
    const params = new URLSearchParams({ limit, offset })
    if (platform) params.append('platform', platform)
    return this.request(`/api/social/posts?${params}`)
  }

  async getSocialMetrics(platform) {
    return this.request(`/api/social/metrics/${platform}`)
  }

  async getSocialAnalytics() {
    return this.request('/api/social/analytics/overview')
  }

  // Social Inbox endpoints
  async getInboxInteractions(params = {}) {
    const searchParams = new URLSearchParams()
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        searchParams.append(key, params[key])
      }
    })
    return this.request(`/api/inbox/interactions?${searchParams}`)
  }

  async updateInteractionStatus(interactionId, status) {
    return this.request(`/api/inbox/interactions/${interactionId}/status`, {
      method: 'PATCH',
      body: { status }
    })
  }

  async generateInteractionResponse(interactionId, personalityStyle = 'professional') {
    return this.request(`/api/inbox/interactions/${interactionId}/generate-response`, {
      method: 'POST',
      body: { personality_style: personalityStyle }
    })
  }

  async sendInteractionResponse(interactionId, responseText) {
    return this.request(`/api/inbox/interactions/${interactionId}/respond`, {
      method: 'POST',
      body: { response_text: responseText }
    })
  }

  async getInboxStats() {
    return this.request('/api/inbox/stats')
  }

  async getResponseTemplates() {
    return this.request('/api/inbox/templates')
  }

  async createResponseTemplate(templateData) {
    return this.request('/api/inbox/templates', {
      method: 'POST',
      body: templateData
    })
  }

  async updateResponseTemplate(templateId, templateData) {
    return this.request(`/api/inbox/templates/${templateId}`, {
      method: 'PUT',
      body: templateData
    })
  }

  async deleteResponseTemplate(templateId) {
    return this.request(`/api/inbox/templates/${templateId}`, {
      method: 'DELETE'
    })
  }

  async getCompanyKnowledge(params = {}) {
    const searchParams = new URLSearchParams()
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        searchParams.append(key, params[key])
      }
    })
    return this.request(`/api/inbox/knowledge?${searchParams}`)
  }

  async createCompanyKnowledge(knowledgeData) {
    return this.request('/api/inbox/knowledge', {
      method: 'POST',
      body: knowledgeData
    })
  }

  async updateCompanyKnowledge(knowledgeId, knowledgeData) {
    return this.request(`/api/inbox/knowledge/${knowledgeId}`, {
      method: 'PUT',
      body: knowledgeData
    })
  }

  async deleteCompanyKnowledge(knowledgeId) {
    return this.request(`/api/inbox/knowledge/${knowledgeId}`, {
      method: 'DELETE'
    })
  }

  // Health and system endpoints
  async getHealth() {
    return this.request('/health')
  }

  async getAuthStatus() {
    return this.request('/api/auth/status')
  }

  async getMemoryStats() {
    return this.request('/api/memory/stats')
  }

  async getGoalsSummary() {
    return this.request('/api/goals/summary')
  }

  // User Settings endpoints
  async getUserSettings() {
    return this.request('/api/user-settings/')
  }

  async updateUserSettings(settings) {
    return this.request('/api/user-settings/', {
      method: 'PUT',
      body: settings
    })
  }

  async getDefaultSettings() {
    return this.request('/api/user-settings/defaults')
  }

  // AI Suggestions endpoints
  async getContextualSuggestions(request) {
    return this.request('/api/ai/suggestions', {
      method: 'POST',
      body: request
    })
  }

  async getSuggestionTypes() {
    return this.request('/api/ai/suggestion-types')
  }
}

// Create singleton instance
const apiService = new ApiService()

export default apiService