import React, { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd'
import Calendar from 'react-calendar'
import { format, addDays, startOfWeek, isSameDay } from 'date-fns'
import 'react-calendar/dist/Calendar.css'
import AccessibleDragDrop from './AccessibleDragDrop'
import KeyboardDragDrop from './KeyboardDragDrop'
import DragDropInstructions from './DragDropInstructions'

// Empty posts array - replace with API calls
const emptyPosts = []

const platforms = [
  { name: 'LinkedIn', color: '#0077B5', icon: '💼' },
  { name: 'Twitter', color: '#1DA1F2', icon: '🐦' },
  { name: 'Instagram', color: '#E4405F', icon: '📸' },
  { name: 'Facebook', color: '#1877F2', icon: '👥' },
]

// Post Card Component
const PostCard = ({ post, index, darkMode }) => {
  const platform = platforms.find((p) => p.name === post.platform)

  const getStatusColor = (status) => {
    switch (status) {
      case 'published':
        return 'bg-green-500'
      case 'scheduled':
        return 'bg-blue-500'
      case 'draft':
        return 'bg-yellow-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <Draggable draggableId={post.id} index={index}>
      {(provided, snapshot) => (
        <motion.div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          className={`p-4 rounded-lg mb-3 border cursor-move transition-all ${
            snapshot.isDragging
              ? 'shadow-lg scale-105'
              : 'shadow-sm hover:shadow-md'
          } ${
            darkMode
              ? 'bg-gray-800 border-gray-700'
              : 'bg-white border-gray-200'
          }`}
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-lg">{platform?.icon}</span>
              <span
                className={`text-sm font-medium ${
                  darkMode ? 'text-white' : 'text-gray-900'
                }`}
              >
                {post.platform}
              </span>
            </div>
            <div
              className={`w-3 h-3 rounded-full ${getStatusColor(post.status)}`}
            />
          </div>

          <h3
            className={`font-semibold mb-2 text-sm ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}
          >
            {post.title}
          </h3>

          <p
            className={`text-xs mb-3 line-clamp-2 ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}
          >
            {post.content}
          </p>

          <div className="flex items-center justify-between">
            <span
              className={`text-xs ${
                darkMode ? 'text-gray-500' : 'text-gray-500'
              }`}
            >
              {format(post.scheduledDate, 'MMM dd, HH:mm')}
            </span>
            <span
              className={`text-xs px-2 py-1 rounded-full capitalize ${
                post.status === 'published'
                  ? 'bg-green-100 text-green-800'
                  : post.status === 'scheduled'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {post.status}
            </span>
          </div>
        </motion.div>
      )}
    </Draggable>
  )
}

// Calendar Day Component
const CalendarDay = ({ date, posts, darkMode }) => {
  const dayPosts = posts.filter((post) =>
    isSameDay(new Date(post.scheduledDate), date)
  )

  return (
    <Droppable droppableId={format(date, 'yyyy-MM-dd')}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.droppableProps}
          className={`min-h-32 p-2 rounded-lg border-2 border-dashed transition-all ${
            snapshot.isDraggedOver
              ? 'border-teal-400 bg-teal-50'
              : darkMode
                ? 'border-gray-700 bg-gray-800/50'
                : 'border-gray-200 bg-gray-50/50'
          }`}
        >
          <div
            className={`text-sm font-medium mb-2 ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}
          >
            {format(date, 'EEE dd')}
          </div>

          <div className="space-y-2">
            {dayPosts.map((post, index) => (
              <PostCard
                key={post.id}
                post={post}
                index={index}
                darkMode={darkMode}
              />
            ))}
          </div>
          {provided.placeholder}
        </div>
      )}
    </Droppable>
  )
}

// Filter Component
const FilterSection = ({
  selectedPlatforms,
  setSelectedPlatforms,
  darkMode,
}) => {
  const togglePlatform = (platformName) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platformName)
        ? prev.filter((p) => p !== platformName)
        : [...prev, platformName]
    )
  }

  return (
    <div
      className={`p-4 rounded-lg ${
        darkMode ? 'bg-gray-800/50' : 'bg-white/50'
      } backdrop-blur-sm border ${
        darkMode ? 'border-gray-700' : 'border-gray-200'
      }`}
    >
      <h3
        className={`text-sm font-semibold mb-3 ${
          darkMode ? 'text-white' : 'text-gray-900'
        }`}
      >
        Filter by Platform
      </h3>
      <div className="flex flex-wrap gap-2">
        {platforms.map((platform) => (
          <button
            key={platform.name}
            onClick={() => togglePlatform(platform.name)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
              selectedPlatforms.includes(platform.name)
                ? 'bg-teal-500 text-white'
                : darkMode
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {platform.icon} {platform.name}
          </button>
        ))}
      </div>
    </div>
  )
}

// Main Content Calendar Component
const ContentCalendar = ({ darkMode, searchQuery }) => {
  const [posts, setPosts] = useState(emptyPosts)
  const [view, setView] = useState('calendar') // 'calendar' or 'list'
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [selectedPlatforms, setSelectedPlatforms] = useState(
    platforms.map((p) => p.name)
  )

  // Handle drag and drop
  const handleDragEnd = useCallback((result) => {
    if (!result.destination) return

    const { source, destination, draggableId } = result

    if (source.droppableId === destination.droppableId) return

    // Update post date based on drop location
    const newDate = new Date(destination.droppableId)

    setPosts((prevPosts) =>
      prevPosts.map((post) =>
        post.id === draggableId ? { ...post, scheduledDate: newDate } : post
      )
    )
  }, [])

  // Filter posts based on selected platforms and search query
  const filteredPosts = posts.filter((post) => {
    const matchesPlatform = selectedPlatforms.includes(post.platform)
    const matchesSearch =
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.content.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesPlatform && matchesSearch
  })

  // Generate calendar days (current week)
  const startDate = startOfWeek(selectedDate)
  const calendarDays = Array.from({ length: 7 }, (_, i) =>
    addDays(startDate, i)
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1
            className={`text-3xl font-bold ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}
          >
            Content Calendar
          </h1>
          <p
            className={`text-lg ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}
          >
            Schedule and manage your social media content
          </p>
        </div>

        {/* View Toggle */}
        <div
          className={`flex rounded-lg p-1 ${
            darkMode ? 'bg-gray-800' : 'bg-gray-100'
          }`}
        >
          <button
            onClick={() => setView('calendar')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              view === 'calendar'
                ? 'bg-teal-500 text-white shadow'
                : darkMode
                  ? 'text-gray-400 hover:text-white'
                  : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📅 Calendar
          </button>
          <button
            onClick={() => setView('list')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              view === 'list'
                ? 'bg-teal-500 text-white shadow'
                : darkMode
                  ? 'text-gray-400 hover:text-white'
                  : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📋 List
          </button>
        </div>
      </motion.div>

      {/* Filter Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <FilterSection
          selectedPlatforms={selectedPlatforms}
          setSelectedPlatforms={setSelectedPlatforms}
          darkMode={darkMode}
        />
      </motion.div>

      {/* Calendar View */}
      {view === 'calendar' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <DragDropInstructions type="calendar" compact={true} />

          <AccessibleDragDrop
            keyboardAlternative={
              <KeyboardDragDrop
                items={filteredPosts.map((post) => ({
                  id: post.id,
                  title: post.title,
                  platform: post.platform,
                  scheduledDate: post.scheduledDate,
                }))}
                dropZones={calendarDays.map((date) => ({
                  id: format(date, 'yyyy-MM-dd'),
                  name: format(date, 'EEE dd'),
                  description: format(date, 'MMMM dd, yyyy'),
                }))}
                onMove={(postId, dateId) => {
                  const newDate = new Date(dateId)
                  setPosts((prevPosts) =>
                    prevPosts.map((post) =>
                      post.id === postId
                        ? { ...post, scheduledDate: newDate }
                        : post
                    )
                  )
                }}
                renderItem={(item, isSelected) => (
                  <div
                    className={`p-4 rounded-lg mb-3 border transition-all ${
                      isSelected
                        ? 'ring-2 ring-blue-500 bg-blue-50'
                        : 'shadow-sm hover:shadow-md'
                    } ${
                      darkMode
                        ? 'bg-gray-800 border-gray-700'
                        : 'bg-white border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">
                          {
                            platforms.find((p) => p.name === item.platform)
                              ?.icon
                          }
                        </span>
                        <span
                          className={`text-sm font-medium ${
                            darkMode ? 'text-white' : 'text-gray-900'
                          }`}
                        >
                          {item.platform}
                        </span>
                      </div>
                    </div>
                    <h3
                      className={`font-semibold mb-2 text-sm ${
                        darkMode ? 'text-white' : 'text-gray-900'
                      }`}
                    >
                      {item.title}
                    </h3>
                  </div>
                )}
                className="mb-6"
              />
            }
            defaultMode="mouse"
            showToggle={true}
            instructions={false}
          >
            <DragDropContext onDragEnd={handleDragEnd}>
              <div className="grid grid-cols-7 gap-4">
                {calendarDays.map((date) => (
                  <CalendarDay
                    key={format(date, 'yyyy-MM-dd')}
                    date={date}
                    posts={filteredPosts}
                    darkMode={darkMode}
                  />
                ))}
              </div>
            </DragDropContext>
          </AccessibleDragDrop>
        </motion.div>
      )}

      {/* List View */}
      {view === 'list' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {filteredPosts
            .sort(
              (a, b) => new Date(a.scheduledDate) - new Date(b.scheduledDate)
            )
            .map((post, index) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
              >
                <PostCard post={post} index={index} darkMode={darkMode} />
              </motion.div>
            ))}
        </motion.div>
      )}

      {/* Stats Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        <div
          className={`p-4 rounded-lg ${
            darkMode ? 'bg-gray-800/50' : 'bg-white/50'
          } backdrop-blur-sm border ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}
        >
          <div className="text-center">
            <p
              className={`text-2xl font-bold ${
                darkMode ? 'text-white' : 'text-gray-900'
              }`}
            >
              {filteredPosts.filter((p) => p.status === 'scheduled').length}
            </p>
            <p
              className={`text-sm ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}
            >
              Scheduled
            </p>
          </div>
        </div>

        <div
          className={`p-4 rounded-lg ${
            darkMode ? 'bg-gray-800/50' : 'bg-white/50'
          } backdrop-blur-sm border ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}
        >
          <div className="text-center">
            <p
              className={`text-2xl font-bold ${
                darkMode ? 'text-white' : 'text-gray-900'
              }`}
            >
              {filteredPosts.filter((p) => p.status === 'draft').length}
            </p>
            <p
              className={`text-sm ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}
            >
              Drafts
            </p>
          </div>
        </div>

        <div
          className={`p-4 rounded-lg ${
            darkMode ? 'bg-gray-800/50' : 'bg-white/50'
          } backdrop-blur-sm border ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}
        >
          <div className="text-center">
            <p
              className={`text-2xl font-bold ${
                darkMode ? 'text-white' : 'text-gray-900'
              }`}
            >
              {filteredPosts.filter((p) => p.status === 'published').length}
            </p>
            <p
              className={`text-sm ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}
            >
              Published
            </p>
          </div>
        </div>

        <div
          className={`p-4 rounded-lg ${
            darkMode ? 'bg-gray-800/50' : 'bg-white/50'
          } backdrop-blur-sm border ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}
        >
          <div className="text-center">
            <p
              className={`text-2xl font-bold ${
                darkMode ? 'text-white' : 'text-gray-900'
              }`}
            >
              {filteredPosts.length}
            </p>
            <p
              className={`text-sm ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}
            >
              Total Posts
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default ContentCalendar
