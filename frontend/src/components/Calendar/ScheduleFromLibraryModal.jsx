import { useState, useEffect, useCallback } from 'react'
import {
  CalendarIcon,
  ClockIcon,
  PhotoIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { useEnhancedApi } from '../../hooks/useEnhancedApi'
import { useNotifications } from '../../hooks/useNotifications'
import FocusTrappedModal from '../FocusTrappedModal'

const platforms = {
  twitter: {
    color: 'bg-sky-500',
    textColor: 'text-sky-500',
    lightBg: 'bg-sky-50',
    label: 'Twitter',
  },
  instagram: {
    color: 'bg-pink-600',
    textColor: 'text-pink-600',
    lightBg: 'bg-pink-50',
    label: 'Instagram',
  },
  facebook: {
    color: 'bg-indigo-600',
    textColor: 'text-indigo-600',
    lightBg: 'bg-indigo-50',
    label: 'Facebook',
  },
}

export default function ScheduleFromLibraryModal({
  isOpen,
  onClose,
  selectedDate,
  onSchedulePost,
}) {
  const [contentLibrary, setContentLibrary] = useState([])
  const [selectedPost, setSelectedPost] = useState(null)
  const [scheduleData, setScheduleData] = useState({
    date: selectedDate || new Date().toISOString().split('T')[0],
    time: '09:00',
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  const { api } = useEnhancedApi()
  const { showSuccess, showError } = useNotifications()

  // Load content library when modal opens
  useEffect(() => {
    if (isOpen) {
      loadContentLibrary()
    }
  }, [isOpen, loadContentLibrary])

  // Update date when selectedDate prop changes
  useEffect(() => {
    if (selectedDate) {
      setScheduleData((prev) => ({ ...prev, date: selectedDate }))
    }
  }, [selectedDate])

  const loadContentLibrary = useCallback(async () => {
    try {
      setIsLoading(true)
      const response = await api.content.getAll(1, 100) // Get more content for selection

      // Filter for draft content that's not already scheduled
      const availableContent = response.filter(
        (item) => item.status === 'draft' || item.status === 'published'
      )

      setContentLibrary(availableContent)
    } catch (error) {
      console.error('Failed to load content library:', error)
      showError('Failed to load content library')
      setContentLibrary([])
    } finally {
      setIsLoading(false)
    }
  }, [api.content, showError])

  const handleSchedulePost = async () => {
    if (!selectedPost) {
      showError('Please select a post to schedule')
      return
    }

    if (!scheduleData.date || !scheduleData.time) {
      showError('Please select both date and time')
      return
    }

    try {
      setIsSaving(true)

      // Update the content item to scheduled status with date/time
      const scheduledDateTime = `${scheduleData.date}T${scheduleData.time}:00`

      await api.content.update(selectedPost.id, {
        status: 'scheduled',
        scheduled_at: scheduledDateTime,
        scheduled_date: scheduledDateTime,
      })

      // Create the scheduled post object for the calendar
      const scheduledPost = {
        id: selectedPost.id,
        title: selectedPost.title,
        content: selectedPost.content,
        platform: selectedPost.platform,
        date: scheduleData.date,
        time: scheduleData.time,
        status: 'scheduled',
        image_url: selectedPost.image_url,
        generated_by_ai: selectedPost.generated_by_ai,
      }

      onSchedulePost(scheduledPost)
      showSuccess(
        `Post scheduled for ${scheduleData.date} at ${scheduleData.time}`
      )
      onClose()

      // Reset state
      setSelectedPost(null)
      setScheduleData({
        date: new Date().toISOString().split('T')[0],
        time: '09:00',
      })
    } catch (error) {
      console.error('Failed to schedule post:', error)
      showError('Failed to schedule post. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  const handlePostSelect = (post) => {
    setSelectedPost(post)
  }

  const getCharacterCount = (content) => {
    return content?.length || 0
  }

  const getPlatformInfo = (platform) => {
    return platforms[platform?.toLowerCase()] || platforms.twitter
  }

  return (
    <FocusTrappedModal
      isOpen={isOpen}
      onClose={onClose}
      title="Schedule Post from Library"
      size="xl"
    >
      <div className="flex h-[calc(90vh-120px)]">
        {/* Content Library Panel */}
        <div className="w-1/2 border-r border-gray-200 p-6 overflow-y-auto">
          <h4 className="font-medium text-gray-900 mb-4">
            Select Post from Content Library
          </h4>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">Loading content...</span>
            </div>
          ) : contentLibrary.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <PhotoIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No content available to schedule</p>
              <p className="text-sm mt-1">
                Create some posts first in the Create Post tab
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {contentLibrary.map((post) => {
                const platformInfo = getPlatformInfo(post.platform)
                const isSelected = selectedPost?.id === post.id

                return (
                  <div
                    key={post.id}
                    onClick={() => handlePostSelect(post)}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500 ring-opacity-20'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h5 className="font-medium text-gray-900 truncate flex-1">
                        {post.title || 'Untitled Post'}
                      </h5>
                      {isSelected && (
                        <CheckCircleIcon className="h-5 w-5 text-blue-500 ml-2 flex-shrink-0" />
                      )}
                    </div>

                    <p className="text-sm text-gray-600 mb-3 line-clamp-3">
                      {post.content.substring(0, 150)}
                      {post.content.length > 150 && '...'}
                    </p>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${platformInfo.lightBg} ${platformInfo.textColor}`}
                        >
                          {platformInfo.label}
                        </span>
                        {post.generated_by_ai && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                            AI Generated
                          </span>
                        )}
                        {post.image_url && (
                          <PhotoIcon
                            className="h-4 w-4 text-gray-400"
                            title="Has image"
                          />
                        )}
                      </div>
                      <span className="text-xs text-gray-500">
                        {getCharacterCount(post.content)} chars
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Scheduling Panel */}
        <div className="w-1/2 p-6 flex flex-col">
          <h4 className="font-medium text-gray-900 mb-4">Schedule Settings</h4>

          {selectedPost ? (
            <div className="flex-1 space-y-6">
              {/* Selected Post Preview */}
              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <h5 className="font-medium text-gray-900 mb-2">
                  Selected Post
                </h5>
                <div
                  className={`p-3 rounded-lg ${getPlatformInfo(selectedPost.platform).lightBg}`}
                >
                  <div className="flex items-start space-x-2">
                    <div
                      className={`w-2 h-2 rounded-full mt-2 ${getPlatformInfo(selectedPost.platform).color}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">
                        {selectedPost.title}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        {selectedPost.content.substring(0, 200)}
                        {selectedPost.content.length > 200 && '...'}
                      </p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className="text-xs text-gray-500">
                          {getPlatformInfo(selectedPost.platform).label}
                        </span>
                        {selectedPost.generated_by_ai && (
                          <>
                            <span className="text-xs text-gray-500">•</span>
                            <span className="text-xs text-gray-500">
                              AI Generated
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {selectedPost.image_url && (
                  <div className="mt-3">
                    <img
                      src={selectedPost.image_url}
                      alt="Post image"
                      className="w-full h-32 object-cover rounded border"
                    />
                  </div>
                )}
              </div>

              {/* Date and Time Selection */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <CalendarIcon className="h-4 w-4 inline mr-1" />
                    Schedule Date
                  </label>
                  <input
                    type="date"
                    value={scheduleData.date}
                    onChange={(e) =>
                      setScheduleData((prev) => ({
                        ...prev,
                        date: e.target.value,
                      }))
                    }
                    min={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <ClockIcon className="h-4 w-4 inline mr-1" />
                    Schedule Time
                  </label>
                  <input
                    type="time"
                    value={scheduleData.time}
                    onChange={(e) =>
                      setScheduleData((prev) => ({
                        ...prev,
                        time: e.target.value,
                      }))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Schedule Summary */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h6 className="font-medium text-blue-900 mb-2">
                  Scheduling Summary
                </h6>
                <div className="text-sm text-blue-800 space-y-1">
                  <p>
                    <strong>Post:</strong> {selectedPost.title}
                  </p>
                  <p>
                    <strong>Platform:</strong>{' '}
                    {getPlatformInfo(selectedPost.platform).label}
                  </p>
                  <p>
                    <strong>Scheduled for:</strong> {scheduleData.date} at{' '}
                    {scheduleData.time}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <CalendarIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>Select a post from the library to schedule it</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSchedulePost}
              disabled={!selectedPost || isSaving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Scheduling...' : 'Schedule Post'}
            </button>
          </div>
        </div>
      </div>
    </FocusTrappedModal>
  )
}
