import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { usePlan } from '../contexts/PlanContext'
import { usePlanConditionals } from '../hooks/usePlanConditionals'
import { useSocialInboxWebSocket } from '../hooks/useWebSocket'
import api from '../services/api'
import TemplateManager from '../components/TemplateManager'
import AIEmptyStateSuggestions from '../components/AIEmptyStatesSuggestions'
import PlanGate from '../components/PlanGate'
import { FeatureGate, TierGate } from '../components/enhanced/EnhancedPlanGate'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  CheckIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  StarIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  UserIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'
import {
  CheckCircleIcon as CheckCircleIconSolid,
  XCircleIcon as XCircleIconSolid,
  ExclamationCircleIcon as ExclamationCircleIconSolid,
  StarIcon as StarIconSolid,
} from '@heroicons/react/24/solid'

const platformColors = {
  facebook: 'bg-blue-100 text-blue-800 border-blue-200',
  instagram: 'bg-pink-100 text-pink-800 border-pink-200',
  twitter: 'bg-sky-100 text-sky-800 border-sky-200',
}

const platformIcons = {
  facebook: '📘',
  instagram: '📷',
  twitter: '🐦',
}

const statusColors = {
  unread: 'bg-red-100 text-red-800 border-red-200',
  read: 'bg-gray-100 text-gray-800 border-gray-200',
  responded: 'bg-green-100 text-green-800 border-green-200',
  archived: 'bg-gray-100 text-gray-800 border-gray-200',
}

const priorityColors = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-green-100 text-green-800',
}

function SocialInbox() {
  const { user } = useAuth()
  const { hasAIInbox } = usePlan()

  // WebSocket connection for real-time updates
  const {
    isConnected,
    newInteractions,
    interactionUpdates,
    responseGenerated,
    responseSent,
    clearNewInteractions,
    clearInteractionUpdates,
    clearResponseGenerated,
    clearResponseSent,
  } = useSocialInboxWebSocket()

  const [activeTab, setActiveTab] = useState('inbox') // 'inbox' or 'templates'
  const [interactions, setInteractions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedInteraction, setSelectedInteraction] = useState(null)
  const [responseText, setResponseText] = useState('')
  const [isGeneratingResponse, setIsGeneratingResponse] = useState(false)
  const [isSendingResponse, setIsSendingResponse] = useState(false)

  // Filters
  const [searchTerm, setSearchTerm] = useState('')
  const [platformFilter, setPlatformFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [intentFilter, setIntentFilter] = useState('all')

  // Pagination and stats
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [stats, setStats] = useState({})

  const fetchInteractions = useCallback(async () => {
    try {
      setLoading(true)
      const params = {
        page,
        per_page: 20,
        search: searchTerm || undefined,
        platform: platformFilter !== 'all' ? platformFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        intent: intentFilter !== 'all' ? intentFilter : undefined,
      }

      const response = await api.getInboxInteractions(params)
      setInteractions(response.interactions || [])
      setTotalPages(response.pagination?.total_pages || 1)
      setStats(response.stats || {})
    } catch (error) {
      console.error('Failed to fetch interactions:', error)
    } finally {
      setLoading(false)
    }
  }, [page, searchTerm, platformFilter, statusFilter, intentFilter])

  useEffect(() => {
    fetchInteractions()
  }, [fetchInteractions])

  // Handle real-time new interactions
  useEffect(() => {
    if (newInteractions.length > 0) {
      newInteractions.forEach((newInteraction) => {
        setInteractions((prev) => {
          // Check if interaction already exists to avoid duplicates
          const exists = prev.some((item) => item.id === newInteraction.id)
          if (!exists) {
            return [newInteraction, ...prev]
          }
          return prev
        })

        // Show browser notification for new interactions (if permission granted)
        if (Notification.permission === 'granted') {
          new Notification('New Social Media Interaction', {
            body: `${newInteraction.author_username} on ${newInteraction.platform}: ${newInteraction.content.substring(0, 100)}...`,
            icon: '/favicon.ico',
          })
        }
      })

      // Update stats
      setStats((prev) => ({
        ...prev,
        total: (prev.total || 0) + newInteractions.length,
        unread: (prev.unread || 0) + newInteractions.length,
      }))

      clearNewInteractions()
    }
  }, [newInteractions, clearNewInteractions])

  // Request notification permission on component mount
  useEffect(() => {
    if (Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  // Handle real-time interaction updates
  useEffect(() => {
    if (interactionUpdates.length > 0) {
      interactionUpdates.forEach((update) => {
        setInteractions((prev) =>
          prev.map((item) =>
            item.id === update.interaction_id
              ? { ...item, ...update.updates }
              : item
          )
        )

        // Update selected interaction if it matches
        if (selectedInteraction?.id === update.interaction_id) {
          setSelectedInteraction((prev) => ({ ...prev, ...update.updates }))
        }
      })

      clearInteractionUpdates()
    }
  }, [interactionUpdates, selectedInteraction?.id, clearInteractionUpdates])

  // Handle real-time response generation
  useEffect(() => {
    if (
      responseGenerated &&
      selectedInteraction?.id === responseGenerated.interaction_id
    ) {
      setResponseText(responseGenerated.response.response_text || '')
      clearResponseGenerated()
    }
  }, [responseGenerated, selectedInteraction?.id, clearResponseGenerated])

  // Handle real-time response sent confirmation
  useEffect(() => {
    if (responseSent) {
      // Update interaction status to responded
      setInteractions((prev) =>
        prev.map((item) =>
          item.id === responseSent.interaction_id
            ? { ...item, status: 'responded' }
            : item
        )
      )

      // Update stats
      setStats((prev) => ({
        ...prev,
        responded: (prev.responded || 0) + 1,
        read: Math.max(0, (prev.read || 0) - 1),
      }))

      // Clear selection if it matches
      if (selectedInteraction?.id === responseSent.interaction_id) {
        setSelectedInteraction(null)
        setResponseText('')
      }

      clearResponseSent()
    }
  }, [responseSent, selectedInteraction?.id, clearResponseSent])

  const handleInteractionSelect = useCallback(async (interaction) => {
    setSelectedInteraction(interaction)
    setResponseText('')

    // Mark as read if it's unread
    if (interaction.status === 'unread') {
      try {
        await api.updateInteractionStatus(interaction.id, 'read')
        // Update the interaction in the list
        setInteractions((prev) =>
          prev.map((item) =>
            item.id === interaction.id ? { ...item, status: 'read' } : item
          )
        )
      } catch (error) {
        console.error('Failed to mark interaction as read:', error)
      }
    }
  }, [])

  const generateResponse = useCallback(
    async (personalityStyle = null) => {
      if (!selectedInteraction) return

      try {
        setIsGeneratingResponse(true)
        // Use null to let backend use user's default personality if no style provided
        const response = await api.generateInteractionResponse(
          selectedInteraction.id,
          personalityStyle || null
        )

        setResponseText(response.response_text || '')
      } catch (error) {
        console.error('Failed to generate response:', error)
      } finally {
        setIsGeneratingResponse(false)
      }
    },
    [selectedInteraction]
  )

  const sendResponse = useCallback(async () => {
    if (!selectedInteraction || !responseText.trim()) return

    try {
      setIsSendingResponse(true)
      await api.sendInteractionResponse(selectedInteraction.id, responseText)

      // Update interaction status to responded
      setInteractions((prev) =>
        prev.map((item) =>
          item.id === selectedInteraction.id
            ? { ...item, status: 'responded' }
            : item
        )
      )

      // Clear selection
      setSelectedInteraction(null)
      setResponseText('')

      // Refresh stats
      fetchInteractions()
    } catch (error) {
      console.error('Failed to send response:', error)
    } finally {
      setIsSendingResponse(false)
    }
  }, [selectedInteraction, responseText, fetchInteractions])

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now - date) / (1000 * 60 * 60))

    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours}h ago`
    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays < 30) return `${diffInDays}d ago`
    return date.toLocaleDateString()
  }

  const getPriorityLevel = (score) => {
    if (score >= 80) return 'high'
    if (score >= 50) return 'medium'
    return 'low'
  }

  return (
    <FeatureGate
      feature="ai_inbox"
      mode="upgrade"
      upgradeTitle="AI Social Inbox - Premium Feature"
      upgradeDescription="Access AI-powered social media inbox management, automated responses, sentiment analysis, and advanced interaction analytics"
      fallbackMode="upgrade-page"
      className="min-h-screen bg-gray-50"
    >
      <div className="h-screen flex flex-col">
        {/* Tab Navigation */}
        <div className="bg-white border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('inbox')}
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'inbox'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <ChatBubbleLeftRightIcon className="h-5 w-5 inline mr-2" />
              Social Inbox
              {stats.unread > 0 && (
                <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  {stats.unread}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('templates')}
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'templates'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <DocumentTextIcon className="h-5 w-5 inline mr-2" />
              Response Templates
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'inbox' ? (
          <>
            {/* Header with stats and filters */}
            <div className="bg-white shadow-sm border-b border-gray-200 p-6">
              {/* Stats cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <div className="bg-blue-100 rounded-md p-3">
                      <ChatBubbleLeftRightIcon className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Total</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {stats.total || 0}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-red-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <div className="bg-red-100 rounded-md p-3">
                      <ExclamationCircleIconSolid className="h-6 w-6 text-red-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">
                        Unread
                      </p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {stats.unread || 0}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-yellow-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <div className="bg-yellow-100 rounded-md p-3">
                      <ClockIcon className="h-6 w-6 text-yellow-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">
                        Pending
                      </p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {stats.read || 0}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <div className="bg-green-100 rounded-md p-3">
                      <CheckCircleIconSolid className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">
                        Responded
                      </p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {stats.responded || 0}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Search and filters */}
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Search interactions..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <select
                  className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  value={platformFilter}
                  onChange={(e) => setPlatformFilter(e.target.value)}
                >
                  <option value="all">All Platforms</option>
                  <option value="facebook">Facebook</option>
                  <option value="instagram">Instagram</option>
                  <option value="twitter">X/Twitter</option>
                </select>

                <select
                  className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Status</option>
                  <option value="unread">Unread</option>
                  <option value="read">Pending</option>
                  <option value="responded">Responded</option>
                </select>

                <select
                  className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  value={intentFilter}
                  onChange={(e) => setIntentFilter(e.target.value)}
                >
                  <option value="all">All Intents</option>
                  <option value="question">Questions</option>
                  <option value="complaint">Complaints</option>
                  <option value="praise">Praise</option>
                  <option value="lead">Sales Leads</option>
                </select>

                <button
                  onClick={fetchInteractions}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  Refresh
                </button>

                {/* WebSocket connection status */}
                <div className="inline-flex items-center px-3 py-2 rounded-md text-sm">
                  <div
                    className={`h-2 w-2 rounded-full mr-2 ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}
                  ></div>
                  <span
                    className={`text-xs ${isConnected ? 'text-green-700' : 'text-red-700'}`}
                  >
                    {isConnected ? 'Live' : 'Offline'}
                  </span>
                </div>
              </div>
            </div>

            {/* Main content */}
            <div className="flex-1 flex overflow-hidden">
              {/* Interactions list */}
              <div className="w-1/2 bg-white border-r border-gray-200 overflow-y-auto">
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                  </div>
                ) : interactions.length === 0 ? (
                  <AIEmptyStateSuggestions
                    type="inbox"
                    context={{
                      hasFilters:
                        platformFilter !== 'all' ||
                        statusFilter !== 'all' ||
                        intentFilter !== 'all',
                      priorityFilter: 'all', // Priority filter not implemented yet
                      selectedPlatform: platformFilter,
                    }}
                    onSuggestionClick={(suggestion) => {
                      switch (suggestion.id) {
                        case 'auto-responses':
                          window.location.href = '/settings#social-inbox'
                          break
                        case 'template-setup':
                          setActiveTab('templates') // Fix: use setActiveTab instead of undefined setShowTemplates
                          break
                        default:
                          window.location.href = '/settings'
                      }
                    }}
                  />
                ) : (
                  <div className="divide-y divide-gray-200">
                    {interactions.map((interaction) => {
                      const priority = getPriorityLevel(
                        interaction.priority_score || 0
                      )
                      return (
                        <div
                          key={interaction.id}
                          className={`p-4 cursor-pointer hover:bg-gray-50 ${
                            selectedInteraction?.id === interaction.id
                              ? 'bg-blue-50 border-r-2 border-blue-500'
                              : ''
                          }`}
                          onClick={() => handleInteractionSelect(interaction)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2 mb-2">
                                <span
                                  className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${platformColors[interaction.platform]}`}
                                >
                                  {platformIcons[interaction.platform]}{' '}
                                  {interaction.platform}
                                </span>
                                <span
                                  className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${statusColors[interaction.status]}`}
                                >
                                  {interaction.status}
                                </span>
                                {priority === 'high' && (
                                  <span
                                    className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${priorityColors[priority]}`}
                                  >
                                    <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                                    High Priority
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center space-x-2 mb-1">
                                <UserIcon className="h-4 w-4 text-gray-400" />
                                <span className="text-sm font-medium text-gray-900">
                                  @{interaction.author_username}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {interaction.interaction_type}
                                </span>
                              </div>

                              <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                                {interaction.content}
                              </p>

                              <div className="flex items-center justify-between text-xs text-gray-500">
                                <span>
                                  {formatTimeAgo(
                                    interaction.platform_created_at
                                  )}
                                </span>
                                {interaction.intent && (
                                  <span className="capitalize">
                                    {interaction.intent}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Interaction details and response */}
              <div className="flex-1 flex flex-col bg-gray-50">
                {selectedInteraction ? (
                  <>
                    {/* Interaction header */}
                    <div className="bg-white border-b border-gray-200 p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-3">
                            <div className="flex-shrink-0">
                              {selectedInteraction.author_profile_image ? (
                                <img
                                  className="h-10 w-10 rounded-full"
                                  src={selectedInteraction.author_profile_image}
                                  alt=""
                                />
                              ) : (
                                <div className="h-10 w-10 bg-gray-300 rounded-full flex items-center justify-center">
                                  <UserIcon className="h-6 w-6 text-gray-500" />
                                </div>
                              )}
                            </div>
                            <div>
                              <h3 className="text-lg font-medium text-gray-900">
                                {selectedInteraction.author_display_name ||
                                  selectedInteraction.author_username}
                              </h3>
                              <p className="text-sm text-gray-500">
                                @{selectedInteraction.author_username}
                              </p>
                            </div>
                            {selectedInteraction.author_verified && (
                              <CheckCircleIconSolid className="h-5 w-5 text-blue-500" />
                            )}
                          </div>

                          <div className="flex items-center space-x-4 text-sm text-gray-500 mb-4">
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${platformColors[selectedInteraction.platform]}`}
                            >
                              {platformIcons[selectedInteraction.platform]}{' '}
                              {selectedInteraction.platform}
                            </span>
                            <span>{selectedInteraction.interaction_type}</span>
                            <span>
                              {formatTimeAgo(
                                selectedInteraction.platform_created_at
                              )}
                            </span>
                            {selectedInteraction.sentiment && (
                              <span className="capitalize">
                                {selectedInteraction.sentiment} sentiment
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-gray-900 whitespace-pre-wrap">
                          {selectedInteraction.content}
                        </p>
                      </div>
                    </div>

                    {/* Response generation */}
                    <div className="flex-1 flex flex-col p-6">
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-3">
                          <label className="text-sm font-medium text-gray-700">
                            Generate Response
                          </label>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => generateResponse(null)}
                              disabled={isGeneratingResponse}
                              className="px-3 py-1 text-xs font-medium rounded-md border-2 border-indigo-300 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                              Default
                            </button>
                            {[
                              'professional',
                              'friendly',
                              'casual',
                              'technical',
                            ].map((style) => (
                              <button
                                key={style}
                                onClick={() => generateResponse(style)}
                                disabled={isGeneratingResponse}
                                className="px-3 py-1 text-xs font-medium rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                              >
                                {style}
                              </button>
                            ))}
                          </div>
                        </div>

                        <textarea
                          className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                          placeholder="Generated response will appear here, or write your own..."
                          value={responseText}
                          onChange={(e) => setResponseText(e.target.value)}
                          disabled={isGeneratingResponse}
                        />

                        {isGeneratingResponse && (
                          <div className="mt-2 flex items-center text-sm text-gray-500">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600 mr-2"></div>
                            Generating AI response...
                          </div>
                        )}
                      </div>

                      <div className="flex justify-end space-x-3">
                        <button
                          onClick={() => setSelectedInteraction(null)}
                          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                          Close
                        </button>
                        <button
                          onClick={sendResponse}
                          disabled={!responseText.trim() || isSendingResponse}
                          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isSendingResponse ? (
                            <>
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
                              Sending...
                            </>
                          ) : (
                            'Send Response'
                          )}
                        </button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center text-gray-500">
                      <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-4" />
                      <p className="text-lg font-medium mb-2">
                        Select an interaction
                      </p>
                      <p>
                        Choose an interaction from the list to view details and
                        respond
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-white border-t border-gray-200 px-6 py-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    Page {page} of {totalPages}
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                      disabled={page === totalPages}
                      className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Templates Tab */
          <div className="flex-1 overflow-y-auto p-6">
            <TemplateManager />
          </div>
        )}
      </div>
    </FeatureGate>
  )
}

export default SocialInbox
