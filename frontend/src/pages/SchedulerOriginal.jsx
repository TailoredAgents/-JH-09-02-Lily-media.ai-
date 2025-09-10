import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ViewColumnsIcon,
  Squares2X2Icon,
  PlusIcon,
  FolderIcon,
} from '@heroicons/react/24/outline'
import DragDropCalendar from '../components/Calendar/DragDropCalendar'
import CreatePostModal from '../components/Calendar/CreatePostModal'
import ScheduleFromLibraryModal from '../components/Calendar/ScheduleFromLibraryModal'
import { useApi } from '../hooks/useApi'
import { useRealTimeContent } from '../hooks/useRealTimeData'
import { error as logError, debug as logDebug } from '../utils/logger.js'

// Mock data for scheduled posts
const scheduledPosts = [
  {
    id: 1,
    title: 'Industry Trends Analysis',
    platform: 'LinkedIn',
    date: '2025-07-23',
    time: '10:00',
    status: 'scheduled',
    content: 'The future of AI in social media marketing...',
  },
  {
    id: 2,
    title: 'Quick Tips Thread',
    platform: 'Twitter',
    date: '2025-07-23',
    time: '15:00',
    status: 'scheduled',
    content: '5 ways to improve your social media engagement...',
  },
  {
    id: 3,
    title: 'Behind the Scenes',
    platform: 'Instagram',
    date: '2025-07-24',
    time: '12:00',
    status: 'draft',
    content: 'A look at our AI content creation process...',
  },
]

const platforms = {
  LinkedIn: { color: 'bg-blue-600', textColor: 'text-blue-600' },
  Twitter: { color: 'bg-sky-500', textColor: 'text-sky-500' },
  Instagram: { color: 'bg-pink-600', textColor: 'text-pink-600' },
  Facebook: { color: 'bg-indigo-600', textColor: 'text-indigo-600' },
}

export default function Scheduler() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [viewMode, setViewMode] = useState('week') // 'month' or 'week'
  const [posts, setPosts] = useState([])
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isLibraryModalOpen, setIsLibraryModalOpen] = useState(false)
  const [selectedDate, setSelectedDate] = useState(null)
  const [_isLoading, setIsLoading] = useState(true)

  const { apiService, makeAuthenticatedRequest } = useApi()
  const { data: upcomingContent, isLoading: _contentLoading } =
    useRealTimeContent()

  const getDaysInMonth = (date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDayOfWeek = firstDay.getDay()

    const days = []

    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null)
    }

    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day)
    }

    return days
  }

  const getPostsForDate = (day) => {
    if (!day) return []
    const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    return posts.filter((post) => post.date === dateStr)
  }

  const navigateMonth = (direction) => {
    const newDate = new Date(currentDate)
    newDate.setMonth(newDate.getMonth() + direction)
    setCurrentDate(newDate)
  }

  const navigateWeek = (direction) => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() + direction * 7)
    setCurrentDate(newDate)
  }

  const navigate = (direction) => {
    if (viewMode === 'week') {
      navigateWeek(direction)
    } else {
      navigateMonth(direction)
    }
  }

  const getWeekDateRange = (date) => {
    const startOfWeek = new Date(date)
    const dayOfWeek = startOfWeek.getDay()
    startOfWeek.setDate(startOfWeek.getDate() - dayOfWeek)

    const endOfWeek = new Date(startOfWeek)
    endOfWeek.setDate(startOfWeek.getDate() + 6)

    const startMonth = monthNames[startOfWeek.getMonth()]
    const endMonth = monthNames[endOfWeek.getMonth()]
    const startDay = startOfWeek.getDate()
    const endDay = endOfWeek.getDate()
    const year = startOfWeek.getFullYear()

    if (startOfWeek.getMonth() === endOfWeek.getMonth()) {
      return `Week of ${startMonth} ${startDay}-${endDay}, ${year}`
    } else {
      return `Week of ${startMonth} ${startDay} - ${endMonth} ${endDay}, ${year}`
    }
  }

  // Load content data on component mount
  useEffect(() => {
    const loadContent = async () => {
      try {
        setIsLoading(true)
        const content = await makeAuthenticatedRequest(apiService.getContent)

        // Transform backend content to calendar post format
        const transformedPosts =
          content.items?.map((item) => ({
            id: item.id,
            title: item.title || 'Untitled Post',
            content: item.content || '',
            platform: item.platform || 'LinkedIn',
            date: item.scheduled_date
              ? item.scheduled_date.split('T')[0]
              : new Date().toISOString().split('T')[0],
            time: item.scheduled_date
              ? new Date(item.scheduled_date).toLocaleTimeString('en-US', {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                })
              : '09:00',
            status: item.status || 'draft',
          })) || []

        setPosts(transformedPosts)
      } catch (error) {
        logError('Failed to load content:', error)
        // Fallback to mock data on error
        setPosts(scheduledPosts)
      } finally {
        setIsLoading(false)
      }
    }

    loadContent()
  }, [apiService, makeAuthenticatedRequest])

  // Update posts when real-time content changes
  useEffect(() => {
    if (upcomingContent && Array.isArray(upcomingContent)) {
      const transformedPosts = upcomingContent.map((item) => ({
        id: item.id,
        title: item.title || 'Untitled Post',
        content: item.content || '',
        platform: item.platform || 'LinkedIn',
        date: item.scheduled_date
          ? item.scheduled_date.split('T')[0]
          : new Date().toISOString().split('T')[0],
        time: item.scheduled_date
          ? new Date(item.scheduled_date).toLocaleTimeString('en-US', {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
            })
          : '09:00',
        status: item.status || 'draft',
      }))
      setPosts(transformedPosts)
    }
  }, [upcomingContent])

  const handleCreatePost = async (newPost) => {
    try {
      // Create content via API
      const contentData = {
        title: newPost.title,
        content: newPost.content,
        platform: newPost.platform.toLowerCase(),
        scheduled_date: `${newPost.date}T${newPost.time}:00`,
        status: newPost.status,
      }

      const createdContent = await makeAuthenticatedRequest(() =>
        apiService.createContent(contentData)
      )

      // Update local state
      const transformedPost = {
        id: createdContent.id,
        title: createdContent.title,
        content: createdContent.content,
        platform: createdContent.platform,
        date: newPost.date,
        time: newPost.time,
        status: createdContent.status,
      }

      setPosts((prev) => [...prev, transformedPost])
    } catch (error) {
      logError('Failed to create content:', error)
      // Fallback to local state update
      setPosts((prev) => [...prev, newPost])
    }
  }

  const handlePostMove = async (post, targetId) => {
    try {
      logDebug('Moving post:', post, 'to:', targetId)

      // Parse targetId - if it's a date, move to that date
      if (targetId.includes('-') && targetId.length === 10) {
        const newDate = targetId
        const updatedPost = { ...post, date: newDate }

        // Update via API
        await makeAuthenticatedRequest(() =>
          apiService.updateContent(post.id, {
            title: post.title,
            content: post.content,
            platform: post.platform.toLowerCase(),
            scheduled_date: `${newDate}T${post.time}:00`,
            status: post.status,
          })
        )

        // Update local state
        setPosts((prev) =>
          prev.map((p) => (p.id === post.id ? updatedPost : p))
        )
      }
    } catch (error) {
      logError('Failed to move post:', error)
    }
  }

  const handleEditPost = async (post) => {
    // This would open an edit modal with the post data
    logDebug('Edit post:', post)
    setSelectedDate(post.date)
    setIsCreateModalOpen(true)
  }

  const handleDuplicatePost = async (post) => {
    const duplicatedPost = {
      ...post,
      id: Date.now(), // Temporary ID until API response
      title: `${post.title} (Copy)`,
      date: post.date,
      time: post.time,
      status: 'draft',
    }

    try {
      // Create duplicate via API
      const contentData = {
        title: duplicatedPost.title,
        content: duplicatedPost.content,
        platform: duplicatedPost.platform.toLowerCase(),
        scheduled_date: `${duplicatedPost.date}T${duplicatedPost.time}:00`,
        status: duplicatedPost.status,
      }

      const createdContent = await makeAuthenticatedRequest(() =>
        apiService.createContent(contentData)
      )

      // Update local state with real ID
      const finalPost = {
        ...duplicatedPost,
        id: createdContent.id,
      }

      setPosts((prev) => [...prev, finalPost])
    } catch (error) {
      logError('Failed to duplicate post:', error)
      // Fallback to local state update
      setPosts((prev) => [...prev, duplicatedPost])
    }
  }

  const handleDeletePost = async (postId) => {
    try {
      await makeAuthenticatedRequest(() => apiService.deleteContent(postId))
      setPosts((prev) => prev.filter((p) => p.id !== postId))
    } catch (error) {
      logError('Failed to delete post:', error)
      // Still remove from local state for UX
      setPosts((prev) => prev.filter((p) => p.id !== postId))
    }
  }

  const handleAddPost = (dateStr) => {
    setSelectedDate(dateStr)
    setIsLibraryModalOpen(true) // Changed to show library modal by default
  }

  // const handleCreateNewPost = (dateStr) => {
  //   setSelectedDate(dateStr)
  //   setIsCreateModalOpen(true)
  // }

  const handleScheduleFromLibrary = (dateStr) => {
    setSelectedDate(dateStr)
    setIsLibraryModalOpen(true)
  }

  const handleSchedulePost = (scheduledPost) => {
    // Add the scheduled post to the posts list
    setPosts((prev) => [...prev, scheduledPost])
  }

  const monthNames = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ]

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  return (
    <div className="space-y-6">
      {/* Calendar Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            {viewMode === 'week'
              ? getWeekDateRange(currentDate)
              : `Month of ${monthNames[currentDate.getMonth()]} ${currentDate.getFullYear()}`}
          </h2>
          <p className="text-sm text-gray-600">
            {viewMode === 'week'
              ? 'Drag and drop to reschedule posts • Colored dots show optimal times'
              : 'Manage your content scheduler and scheduled posts'}
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {/* View Toggle */}
          <div className="flex items-center bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('month')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center space-x-1 ${
                viewMode === 'month'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Squares2X2Icon className="h-4 w-4" />
              <span>Month</span>
            </button>
            <button
              onClick={() => setViewMode('week')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center space-x-1 ${
                viewMode === 'week'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <ViewColumnsIcon className="h-4 w-4" />
              <span>Week</span>
            </button>
          </div>

          {/* Navigation */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigate(-1)}
              className="p-2 rounded-md border border-gray-300 bg-white hover:bg-gray-50"
            >
              <ChevronLeftIcon className="h-5 w-5" />
            </button>
            <button
              onClick={() => setCurrentDate(new Date())}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              {viewMode === 'week' ? 'This Week' : 'This Month'}
            </button>
            <button
              onClick={() => navigate(1)}
              className="p-2 rounded-md border border-gray-300 bg-white hover:bg-gray-50"
            >
              <ChevronRightIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Calendar Views */}
      {viewMode === 'week' ? (
        <DragDropCalendar
          posts={posts}
          onPostMove={handlePostMove}
          onAddPost={handleAddPost}
          onEditPost={handleEditPost}
          onDuplicatePost={handleDuplicatePost}
          onDeletePost={handleDeletePost}
        />
      ) : (
        <div className="bg-white rounded-lg shadow">
          <div className="grid grid-cols-7 border-b border-gray-200">
            {dayNames.map((day) => (
              <div
                key={day}
                className="p-4 text-center text-sm font-medium text-gray-500"
              >
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {getDaysInMonth(currentDate).map((day, index) => {
              const posts = getPostsForDate(day)
              const isToday =
                day === new Date().getDate() &&
                currentDate.getMonth() === new Date().getMonth() &&
                currentDate.getFullYear() === new Date().getFullYear()

              return (
                <div
                  key={index}
                  className={`min-h-32 p-2 border-r border-b border-gray-200 ${
                    day ? 'hover:bg-gray-50 cursor-pointer' : ''
                  }`}
                  onClick={() =>
                    day &&
                    handleAddPost(
                      `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                    )
                  }
                >
                  {day && (
                    <>
                      <div
                        className={`text-sm font-medium ${
                          isToday ? 'text-blue-600' : 'text-gray-900'
                        }`}
                      >
                        {isToday && (
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white text-xs">
                            {day}
                          </span>
                        )}
                        {!isToday && day}
                      </div>

                      <div className="mt-1 space-y-1">
                        {posts.map((post) => (
                          <div
                            key={post.id}
                            className={`text-xs p-1 rounded truncate ${
                              platforms[post.platform]?.color || 'bg-gray-500'
                            } text-white cursor-pointer hover:opacity-80`}
                            title={`${post.time} - ${post.title}`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            {post.time} {post.platform}
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Upcoming Posts */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Upcoming Posts</h3>
          <div className="flex space-x-2">
            <button
              onClick={() =>
                handleScheduleFromLibrary(
                  new Date().toISOString().split('T')[0]
                )
              }
              className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors flex items-center space-x-2"
            >
              <FolderIcon className="h-4 w-4" />
              <span>Schedule from Library</span>
            </button>
            <Link
              to="/create-post"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <PlusIcon className="h-4 w-4" />
              <span>Create New Post</span>
            </Link>
          </div>
        </div>
        <div className="space-y-3">
          {posts
            .filter(
              (post) => new Date(post.date + 'T' + post.time) >= new Date()
            )
            .sort(
              (a, b) =>
                new Date(a.date + 'T' + a.time) -
                new Date(b.date + 'T' + b.time)
            )
            .slice(0, 5)
            .map((post) => (
              <div
                key={post.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-3 h-3 rounded-full ${platforms[post.platform]?.color}`}
                  />
                  <div>
                    <p className="font-medium text-gray-900">{post.title}</p>
                    <p className="text-sm text-gray-500">
                      {post.content.substring(0, 80)}...
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {post.date}
                  </p>
                  <p className="text-sm text-gray-500">
                    {post.time} • {post.platform}
                  </p>
                  <p
                    className={`text-xs px-2 py-1 rounded-full inline-block mt-1 ${
                      post.status === 'scheduled'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {post.status}
                  </p>
                </div>
              </div>
            ))}
          {posts.filter(
            (post) => new Date(post.date + 'T' + post.time) >= new Date()
          ).length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <p>No upcoming posts scheduled</p>
              <div className="flex justify-center space-x-4 mt-4">
                <button
                  onClick={() =>
                    handleScheduleFromLibrary(
                      new Date().toISOString().split('T')[0]
                    )
                  }
                  className="text-blue-600 hover:text-blue-700 font-medium text-sm underline"
                >
                  Schedule from Library
                </button>
                <span className="text-gray-400">or</span>
                <Link
                  to="/create-post"
                  className="text-blue-600 hover:text-blue-700 font-medium text-sm underline"
                >
                  Create New Post
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Post Modal */}
      <CreatePostModal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false)
          setSelectedDate(null)
        }}
        selectedDate={selectedDate}
        onCreatePost={handleCreatePost}
      />

      {/* Schedule from Library Modal */}
      <ScheduleFromLibraryModal
        isOpen={isLibraryModalOpen}
        onClose={() => {
          setIsLibraryModalOpen(false)
          setSelectedDate(null)
        }}
        selectedDate={selectedDate}
        onSchedulePost={handleSchedulePost}
      />
    </div>
  )
}
