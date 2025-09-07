import { useState, useEffect, useMemo, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEnhancedApi } from '../hooks/useEnhancedApi'
import { useNotifications } from '../hooks/useNotifications'
import { usePlan } from '../contexts/PlanContext'
import { error as logError, debug as logDebug } from '../utils/logger.js'
import apiService from '../services/api'
import { ApiErrorBoundary } from '../components/ErrorBoundary'
import AIEmptyStateSuggestions from '../components/AIEmptyStatesSuggestions'
import EnhancedSearch from '../components/EnhancedSearch'
import PlanGate from '../components/PlanGate'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  DocumentTextIcon,
  PhotoIcon,
  ChartBarIcon,
  CalendarIcon,
  ArrowPathIcon,
  HeartIcon,
  ShareIcon,
  EyeIcon,
  ChartPieIcon,
  BoltIcon,
  XMarkIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import SimilarityChart from '../components/Memory/SimilarityChart'
import ContentDetailModal from '../components/Memory/ContentDetailModal'

// Content types for filtering

const contentTypes = [
  { value: 'all', label: 'All Content', icon: DocumentTextIcon },
  { value: 'research', label: 'Research', icon: ChartBarIcon },
  { value: 'content', label: 'Posts', icon: DocumentTextIcon },
  { value: 'image', label: 'Images', icon: PhotoIcon },
  { value: 'competitor_analysis', label: 'Analysis', icon: FunnelIcon },
]

const platforms = [
  { value: 'all', label: 'All Platforms' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'twitter', label: 'Twitter' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'research', label: 'Research' },
  { value: 'web', label: 'Web' },
]

export default function MemoryExplorer() {
  const { hasPremiumAI } = usePlan()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all') // Added missing selectedCategory state
  const [selectedPlatform, setSelectedPlatform] = useState('all')
  const [sortBy, setSortBy] = useState('created_at')
  const [selectedContent, setSelectedContent] = useState(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showSimilarityChart, setShowSimilarityChart] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [editingContent, setEditingContent] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [filteredContent, setFilteredContent] = useState([])

  const { api, connectionStatus, makeAuthenticatedRequest } = useEnhancedApi()
  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotifications()

  // Fetch all memory content
  const {
    data: allMemoryContent = [],
    isLoading: memoryLoading,
    error: memoryError,
  } = useQuery({
    queryKey: ['memory', 'all', currentPage],
    queryFn: () => api.memory.getAll(currentPage, 20),
    staleTime: 2 * 60 * 1000,
    retry: 2,
    fallbackData: [],
  })

  // Search memory content
  const {
    data: searchResults = [],
    isLoading: searchLoading,
    error: searchError,
  } = useQuery({
    queryKey: ['memory', 'search', searchQuery],
    queryFn: () => api.memory.search(searchQuery, 10),
    enabled: searchQuery.length > 2,
    staleTime: 1 * 60 * 1000,
    retry: 1,
  })

  // Get memory analytics
  const { data: memoryAnalytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['memory', 'analytics'],
    queryFn: api.memory.getAnalytics,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })

  // Store memory mutation
  const storeMemoryMutation = useMutation({
    mutationFn: ({ content, metadata }) => api.memory.store(content, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] })
    },
    onError: (error) => {
      logError('Failed to store memory:', error)
    },
  })

  // Update memory mutation
  const updateMemoryMutation = useMutation({
    mutationFn: ({ contentId, data }) => api.memory.update(contentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] })
      setShowDetailModal(false)
    },
    onError: (error) => {
      logError('Failed to update memory:', error)
    },
  })

  // Delete memory mutation
  const deleteMemoryMutation = useMutation({
    mutationFn: api.memory.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] })
      setShowDetailModal(false)
    },
    onError: (error) => {
      logError('Failed to delete memory:', error)
    },
  })

  // Initialize filtered content when memory data loads
  useEffect(() => {
    if (allMemoryContent && allMemoryContent.length > 0) {
      setFilteredContent(allMemoryContent)
    }
  }, [allMemoryContent])

  // Filter content based on search and filters
  useEffect(() => {
    const performSearch = async () => {
      setIsSearching(true)

      try {
        // If there's a search query, try FAISS similarity search first
        if (searchQuery && searchQuery.length > 2) {
          try {
            const searchResults = await makeAuthenticatedRequest(
              apiService.searchMemory,
              searchQuery,
              10
            )

            if (searchResults && searchResults.length > 0) {
              // Use real search results from FAISS
              let filtered = searchResults

              // Apply additional filters
              if (selectedType !== 'all') {
                filtered = filtered.filter(
                  (item) => item.metadata?.type === selectedType
                )
              }

              if (selectedPlatform !== 'all') {
                filtered = filtered.filter(
                  (item) => item.metadata?.platform === selectedPlatform
                )
              }

              setFilteredContent(
                filtered.map((result) => ({
                  id: result.content_id,
                  title: result.metadata?.title || 'Untitled',
                  content: result.content || '',
                  type: result.metadata?.type || 'content',
                  platform: result.metadata?.platform || 'unknown',
                  engagement: result.metadata?.engagement || {
                    likes: 0,
                    shares: 0,
                    views: 0,
                  },
                  created_at: result.created_at,
                  tags: result.metadata?.tags || [],
                  similarity_score: result.similarity_score,
                  repurpose_suggestions: Math.floor(Math.random() * 5) + 1,
                }))
              )
              setIsSearching(false)
              return
            }
          } catch (error) {
            logDebug('FAISS search not available, using local search:', error)
          }
        }

        // Fallback to local filtering using actual memory data
        let filtered = allMemoryContent || []

        // Search filter
        if (searchQuery) {
          filtered = filtered.filter(
            (item) =>
              item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
              item.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
              item.tags.some((tag) =>
                tag.toLowerCase().includes(searchQuery.toLowerCase())
              )
          )
        }

        // Type filter
        if (selectedType !== 'all') {
          filtered = filtered.filter((item) => item.type === selectedType)
        }

        // Platform filter
        if (selectedPlatform !== 'all') {
          filtered = filtered.filter(
            (item) => item.platform === selectedPlatform
          )
        }

        // Sort
        filtered.sort((a, b) => {
          switch (sortBy) {
            case 'engagement':
              return (
                b.engagement.likes +
                b.engagement.shares -
                (a.engagement.likes + a.engagement.shares)
              )
            case 'similarity':
              return b.similarity_score - a.similarity_score
            case 'repurpose':
              return b.repurpose_suggestions - a.repurpose_suggestions
            default: // created_at
              return new Date(b.created_at) - new Date(a.created_at)
          }
        })

        setFilteredContent(filtered)
      } catch (error) {
        logError('Search failed:', error)
        setFilteredContent(allMemoryContent || [])
      } finally {
        setIsSearching(false)
      }
    }

    const searchTimeout = setTimeout(performSearch, searchQuery ? 300 : 0)
    return () => clearTimeout(searchTimeout)
  }, [
    searchQuery,
    selectedType,
    selectedPlatform,
    sortBy,
    apiService,
    makeAuthenticatedRequest,
  ])

  const getTypeIcon = useCallback((type) => {
    const typeConfig = contentTypes.find((t) => t.value === type)
    const Icon = typeConfig?.icon || DocumentTextIcon
    return Icon
  }, [])

  const getEngagementTotal = useCallback((engagement) => {
    return (engagement.likes || 0) + (engagement.shares || 0)
  }, [])

  const formatDate = useCallback((dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      time: 'short',
    })
  }, [])

  const handleContentClick = useCallback((content) => {
    setSelectedContent(content)
    setShowDetailModal(true)
  }, [])

  const handleNodeClick = useCallback(
    (contentId) => {
      const content = filteredContent.find((item) => item.id === contentId)
      if (content) {
        handleContentClick(content)
      }
    },
    [filteredContent, handleContentClick]
  )

  const handleRepurpose = async (content, option = null) => {
    logDebug('Repurposing content:', content, 'with option:', option)

    try {
      // Generate repurposed content using the workflow system
      const repurposeData = {
        source_content: content.content,
        source_title: content.title,
        target_platform: option?.platform || 'general',
        repurpose_type: option?.id || 'general',
        metadata: {
          original_id: content.id,
          original_platform: content.platform,
          repurpose_option: option,
        },
      }

      const result = await makeAuthenticatedRequest(
        apiService.generateContent,
        `Repurpose this content for ${option?.title || 'general use'}: ${content.content}`,
        option?.id || 'text'
      )

      if (result) {
        showSuccess(
          `Content repurposed successfully for ${option?.platform || 'general use'}!`,
          'Repurpose Complete'
        )

        // Optionally store the repurposed content in memory
        const newContent = {
          content: result.content || result,
          metadata: {
            type: 'repurposed',
            original_id: content.id,
            target_platform: option?.platform,
            repurpose_type: option?.id,
          },
        }

        await storeMemoryMutation.mutateAsync(newContent)
      }
    } catch (error) {
      logError('Failed to repurpose content:', error)
      showError(
        'Failed to repurpose content. Please try again.',
        'Repurpose Failed'
      )
    }

    setShowDetailModal(false)
  }

  const handleEdit = (content) => {
    logDebug('Editing content:', content)

    // Close the detail modal and open edit interface
    setShowDetailModal(false)

    // Set the content to be edited
    setEditingContent({
      id: content.id,
      title: content.title,
      content: content.content,
      type: content.type,
      platform: content.platform,
      tags: content.tags || [],
    })

    // Show edit modal/form
    setShowEditModal(true)
  }

  const handleDelete = async (contentId) => {
    logDebug('Deleting content:', contentId)

    // Show confirmation dialog
    const confirmed = window.confirm(
      'Are you sure you want to delete this content? This action cannot be undone.'
    )

    if (!confirmed) {
      return
    }

    try {
      await deleteMemoryMutation.mutateAsync(contentId)
      showSuccess('Content deleted successfully!', 'Delete Complete')
    } catch (error) {
      logError('Failed to delete content:', error)
      showError('Failed to delete content. Please try again.', 'Delete Failed')
    }

    setShowDetailModal(false)
  }

  const handleSaveEdit = async () => {
    if (!editingContent) return

    try {
      await updateMemoryMutation.mutateAsync({
        contentId: editingContent.id,
        data: {
          title: editingContent.title,
          content: editingContent.content,
          metadata: {
            type: editingContent.type,
            platform: editingContent.platform,
            tags: editingContent.tags,
            updated_at: new Date().toISOString(),
          },
        },
      })

      showSuccess('Content updated successfully!', 'Update Complete')
      setShowEditModal(false)
      setEditingContent(null)
    } catch (error) {
      logError('Failed to update content:', error)
      showError('Failed to update content. Please try again.', 'Update Failed')
    }
  }

  return (
    <PlanGate
      feature="premium_ai_models"
      showUpgradePrompt={true}
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
            <div className="mb-6">
              <BoltIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Brand Brain Memory Explorer
              </h2>
              <p className="text-gray-600 mb-6">
                Upgrade your plan to access advanced AI memory capabilities,
                content analysis, and intelligent insights from your brand's
                content history.
              </p>
              <button
                onClick={() => (window.location.href = '/billing')}
                className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
              >
                Upgrade to Access Brand Brain
              </button>
            </div>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Memory Explorer
            </h2>
            <p className="text-sm text-gray-600">
              Search and explore your content history, research, and insights
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowSimilarityChart(!showSimilarityChart)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                showSimilarityChart
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <ChartPieIcon className="h-4 w-4 inline mr-2" />
              Similarity View
            </button>

            <button className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors flex items-center space-x-2">
              <BoltIcon className="h-4 w-4" />
              <span>Auto-Repurpose</span>
            </button>
          </div>
        </div>

        {/* Enhanced Search and Filters */}
        <div
          className="bg-white rounded-lg shadow p-6"
          role="search"
          aria-labelledby="search-filters-heading"
        >
          <h2 id="search-filters-heading" className="sr-only">
            Search and filter content
          </h2>

          <EnhancedSearch
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            filters={{
              type: selectedType,
              platform: selectedPlatform,
              sortBy: sortBy,
            }}
            onFiltersChange={(newFilters) => {
              if (newFilters.type !== undefined)
                setSelectedType(newFilters.type)
              if (newFilters.platform !== undefined)
                setSelectedPlatform(newFilters.platform)
              if (newFilters.sortBy !== undefined) setSortBy(newFilters.sortBy)
            }}
            suggestions={[
              {
                text: 'viral content patterns',
                icon: SparklesIcon,
                type: 'search',
              },
              {
                text: 'engagement optimization ideas',
                icon: ChartBarIcon,
                type: 'search',
              },
              {
                text: 'competitor analysis insights',
                icon: FunnelIcon,
                type: 'search',
              },
              {
                text: 'repurpose-ready content',
                icon: ArrowPathIcon,
                type: 'filter',
              },
              {
                text: 'research and insights',
                icon: DocumentTextIcon,
                type: 'filter',
              },
            ]}
            placeholder="Search your brand brain with AI semantic similarity..."
            showAdvanced={true}
            className="mb-4"
          />

          {/* Traditional Filter Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Content Type Filter */}
            <div>
              <label htmlFor="content-type-filter" className="sr-only">
                Filter by content type
              </label>
              <select
                id="content-type-filter"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm w-full"
                aria-label="Filter by content type"
              >
                {contentTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Platform Filter */}
            <div>
              <label htmlFor="platform-filter" className="sr-only">
                Filter by platform
              </label>
              <select
                id="platform-filter"
                value={selectedPlatform}
                onChange={(e) => setSelectedPlatform(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm w-full"
                aria-label="Filter by platform"
              >
                {platforms.map((platform) => (
                  <option key={platform.value} value={platform.value}>
                    {platform.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Sort By */}
            <div>
              <label htmlFor="sort-by" className="sr-only">
                Sort content by
              </label>
              <select
                id="sort-by"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm w-full"
                aria-label="Sort content by"
              >
                <option value="created_at">Latest First</option>
                <option value="engagement">Most Engaging</option>
                <option value="similarity">Most Similar</option>
                <option value="repurpose">Repurpose Ready</option>
              </select>
            </div>

            {/* Results Count */}
            <div className="flex items-center justify-center">
              <span className="text-sm text-gray-600">
                {filteredContent.length}{' '}
                {filteredContent.length === 1 ? 'item' : 'items'} found
                {isSearching && (
                  <span className="ml-2">
                    <div className="inline-block animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                  </span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Similarity Chart */}
        {showSimilarityChart && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Content Similarity Map
            </h3>
            <SimilarityChart
              content={filteredContent}
              onNodeClick={handleNodeClick}
            />
            <p className="text-sm text-gray-500 mt-2">
              Click on nodes to view detailed content information.
              {filteredContent.length > 0 &&
                ` Showing ${filteredContent.length} content items.`}
            </p>
          </div>
        )}

        {/* Content Grid */}
        <div
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          role="list"
          aria-label="Content items"
        >
          {filteredContent.map((item) => {
            const Icon = getTypeIcon(item.type)
            const engagementTotal = getEngagementTotal(item.engagement)

            return (
              <article
                key={item.id}
                className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow focus-within:ring-2 focus-within:ring-blue-500"
                role="listitem"
                aria-labelledby={`content-title-${item.id}`}
              >
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <Icon
                        className="h-6 w-6 text-blue-600"
                        aria-hidden="true"
                      />
                      <div>
                        <h3
                          id={`content-title-${item.id}`}
                          className="font-semibold text-gray-900 line-clamp-1"
                        >
                          {item.title}
                        </h3>
                        <div className="flex items-center space-x-2 mt-1">
                          <span
                            className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full"
                            role="text"
                          >
                            Platform: {item.platform}
                          </span>
                          <time
                            className="text-xs text-gray-500"
                            dateTime={item.created_at}
                          >
                            {formatDate(item.created_at)}
                          </time>
                        </div>
                      </div>
                    </div>

                    {item.similarity_score && (
                      <div className="text-right">
                        <div
                          className="text-sm font-medium text-green-600"
                          aria-label={`Similarity match: ${Math.round(item.similarity_score * 100)} percent`}
                        >
                          {Math.round(item.similarity_score * 100)}% match
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Content Preview */}
                  <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                    {item.content}
                  </p>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1 mb-4">
                    {item.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded-full"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>

                  {/* Stats */}
                  <div className="flex items-center justify-between text-sm text-gray-500">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-1">
                        <HeartIcon className="h-4 w-4" />
                        <span>{item.engagement.likes}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <ShareIcon className="h-4 w-4" />
                        <span>{item.engagement.shares}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <EyeIcon className="h-4 w-4" />
                        <span>{item.engagement.views}</span>
                      </div>
                    </div>

                    {item.repurpose_suggestions > 0 && (
                      <div className="flex items-center space-x-1">
                        <ArrowPathIcon className="h-4 w-4 text-green-600" />
                        <span className="text-green-600 font-medium">
                          {item.repurpose_suggestions} repurpose ideas
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div
                    className="flex space-x-2 mt-4"
                    role="group"
                    aria-label={`Actions for ${item.title}`}
                  >
                    <button
                      onClick={() => handleRepurpose(item)}
                      className="flex-1 bg-blue-600 text-white px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                      aria-describedby={`repurpose-desc-${item.id}`}
                    >
                      Repurpose Content
                    </button>
                    <div id={`repurpose-desc-${item.id}`} className="sr-only">
                      Generate new content variations from this item
                    </div>
                    <button
                      onClick={() => handleContentClick(item)}
                      className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                      aria-describedby={`details-desc-${item.id}`}
                    >
                      View Details
                    </button>
                    <div id={`details-desc-${item.id}`} className="sr-only">
                      View full content details and additional options
                    </div>
                  </div>
                </div>
              </article>
            )
          })}
        </div>

        {/* Empty State */}
        {filteredContent.length === 0 && !isSearching && (
          <AIEmptyStateSuggestions
            type="memory"
            context={{
              hasSearch: !!searchQuery,
              searchQuery,
              selectedCategory,
              selectedPlatform,
            }}
            onSuggestionClick={(suggestion) => {
              switch (suggestion.id) {
                case 'import-content':
                  window.location.href = '/create-post?mode=import'
                  break
                case 'semantic-search':
                  // Focus search input
                  document
                    .querySelector('input[placeholder*="Search"]')
                    ?.focus()
                  break
                default:
                  window.location.href = '/create-post'
              }
            }}
          />
        )}

        {/* Loading State */}
        {isSearching && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              Searching...
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Finding similar content using AI-powered semantic search
            </p>
          </div>
        )}

        {/* Detail Modal */}
        <ContentDetailModal
          content={selectedContent}
          isOpen={showDetailModal}
          onClose={() => setShowDetailModal(false)}
          onRepurpose={handleRepurpose}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />

        {/* Edit Modal */}
        {showEditModal && editingContent && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Edit Content
                </h3>
                <button
                  onClick={() => {
                    setShowEditModal(false)
                    setEditingContent(null)
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Title
                  </label>
                  <input
                    type="text"
                    value={editingContent.title}
                    onChange={(e) =>
                      setEditingContent({
                        ...editingContent,
                        title: e.target.value,
                      })
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Content
                  </label>
                  <textarea
                    value={editingContent.content}
                    onChange={(e) =>
                      setEditingContent({
                        ...editingContent,
                        content: e.target.value,
                      })
                    }
                    rows={8}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Type
                    </label>
                    <select
                      value={editingContent.type}
                      onChange={(e) =>
                        setEditingContent({
                          ...editingContent,
                          type: e.target.value,
                        })
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="content">Content</option>
                      <option value="research">Research</option>
                      <option value="image">Image</option>
                      <option value="video">Video</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Platform
                    </label>
                    <select
                      value={editingContent.platform}
                      onChange={(e) =>
                        setEditingContent({
                          ...editingContent,
                          platform: e.target.value,
                        })
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="twitter">Twitter</option>
                      <option value="instagram">Instagram</option>
                      <option value="web">Web</option>
                      <option value="research">Research</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tags (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editingContent.tags?.join(', ') || ''}
                    onChange={(e) =>
                      setEditingContent({
                        ...editingContent,
                        tags: e.target.value
                          .split(',')
                          .map((tag) => tag.trim())
                          .filter((tag) => tag),
                      })
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="AI, Marketing, Trends"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => {
                    setShowEditModal(false)
                    setEditingContent(null)
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={updateMemoryMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {updateMemoryMutation.isPending
                    ? 'Saving...'
                    : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PlanGate>
  )
}
