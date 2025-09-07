import React, { useState, useMemo, useCallback } from 'react'
import { debug as logDebug } from '../../utils/logger.js'
import DragDropInstructions from '../DragDropInstructions'
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  rectIntersection,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useDroppable } from '@dnd-kit/core'
import { format, addDays, startOfWeek, isSameDay, parseISO } from 'date-fns'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  PlusIcon,
  ClockIcon,
  FireIcon,
  ChartBarIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  EllipsisHorizontalIcon,
  ArrowsRightLeftIcon,
} from '@heroicons/react/24/outline'

// Optimal posting times data (mock - will come from backend analytics)
const optimalTimes = {
  monday: [
    { hour: 9, score: 85 },
    { hour: 15, score: 92 },
    { hour: 18, score: 78 },
  ],
  tuesday: [
    { hour: 10, score: 88 },
    { hour: 14, score: 85 },
    { hour: 19, score: 82 },
  ],
  wednesday: [
    { hour: 11, score: 90 },
    { hour: 16, score: 94 },
    { hour: 20, score: 79 },
  ],
  thursday: [
    { hour: 9, score: 87 },
    { hour: 13, score: 91 },
    { hour: 17, score: 86 },
  ],
  friday: [
    { hour: 8, score: 89 },
    { hour: 12, score: 88 },
    { hour: 16, score: 84 },
  ],
  saturday: [
    { hour: 10, score: 76 },
    { hour: 14, score: 82 },
    { hour: 19, score: 88 },
  ],
  sunday: [
    { hour: 11, score: 79 },
    { hour: 15, score: 86 },
    { hour: 18, score: 91 },
  ],
}

const platforms = {
  LinkedIn: {
    color: 'bg-blue-600',
    textColor: 'text-blue-600',
    lightBg: 'bg-blue-50',
  },
  Twitter: {
    color: 'bg-sky-500',
    textColor: 'text-sky-500',
    lightBg: 'bg-sky-50',
  },
  Instagram: {
    color: 'bg-pink-600',
    textColor: 'text-pink-600',
    lightBg: 'bg-pink-50',
  },
  Facebook: {
    color: 'bg-indigo-600',
    textColor: 'text-indigo-600',
    lightBg: 'bg-indigo-50',
  },
}

// Enhanced draggable post item component with actions
const DraggablePostItem = React.memo(function DraggablePostItem({
  post,
  isDragging,
  onEdit,
  onDuplicate,
  onDelete,
  isSelected,
  onSelect,
}) {
  const [showActions, setShowActions] = useState(false)
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: post.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const getOptimalityScore = (dayOfWeek, hour) => {
    const dayName = [
      'sunday',
      'monday',
      'tuesday',
      'wednesday',
      'thursday',
      'friday',
      'saturday',
    ][dayOfWeek]
    const dayOptimal = optimalTimes[dayName] || []
    const closest = dayOptimal.reduce(
      (prev, curr) =>
        Math.abs(curr.hour - hour) < Math.abs(prev.hour - hour) ? curr : prev,
      { hour: 12, score: 50 }
    )
    return closest.score
  }

  const postDate = parseISO(post.date + 'T' + post.time)
  const optimalityScore = getOptimalityScore(
    postDate.getDay(),
    postDate.getHours()
  )

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative p-3 rounded-lg border cursor-move transition-all hover:shadow-md group ${
        platforms[post.platform]?.lightBg || 'bg-gray-50'
      } ${isDragging ? 'shadow-lg ring-2 ring-blue-400' : 'shadow-sm'} ${
        isSelected ? 'ring-2 ring-blue-500' : ''
      }`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Selection checkbox */}
      <div className="absolute top-1 left-1">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => {
            e.stopPropagation()
            onSelect(post.id, e.target.checked)
          }}
          className="w-3 h-3 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
        />
      </div>

      {/* Optimality indicator */}
      <div className="absolute top-1 right-1 flex items-center space-x-1">
        {optimalityScore >= 90 && <FireIcon className="h-3 w-3 text-red-500" />}
        {optimalityScore >= 80 && optimalityScore < 90 && (
          <ChartBarIcon className="h-3 w-3 text-orange-500" />
        )}
        {optimalityScore < 80 && (
          <ClockIcon className="h-3 w-3 text-gray-400" />
        )}
        <span className="text-xs font-medium text-gray-600">
          {optimalityScore}%
        </span>
      </div>

      {/* Quick actions (shown on hover) */}
      {showActions && (
        <div className="absolute top-1 right-12 flex items-center space-x-1 bg-white rounded-md shadow-sm border opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit(post)
            }}
            className="p-1 hover:bg-gray-100 rounded"
            title="Edit post"
          >
            <PencilIcon className="h-3 w-3 text-gray-600" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDuplicate(post)
            }}
            className="p-1 hover:bg-gray-100 rounded"
            title="Duplicate post"
          >
            <DocumentDuplicateIcon className="h-3 w-3 text-gray-600" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(post.id)
            }}
            className="p-1 hover:bg-red-100 rounded"
            title="Delete post"
          >
            <TrashIcon className="h-3 w-3 text-red-600" />
          </button>
        </div>
      )}

      <div
        className="flex items-start space-x-2 mt-2"
        {...attributes}
        {...listeners}
      >
        <div
          className={`w-2 h-2 rounded-full mt-2 ${platforms[post.platform]?.color}`}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {post.title}
          </p>
          <p className="text-xs text-gray-500 truncate">{post.content}</p>
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs font-medium text-gray-600">
              {post.time}
            </span>
            <span className="text-xs text-gray-500">{post.platform}</span>
            <span
              className={`text-xs px-1.5 py-0.5 rounded-full ${
                post.status === 'scheduled'
                  ? 'bg-green-100 text-green-800'
                  : post.status === 'published'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {post.status}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
})

// Enhanced droppable day cell component with time slots
const DroppableDay = React.memo(function DroppableDay({
  day,
  date,
  posts,
  currentDate,
  onAddPost,
  selectedPosts,
  onSelectPost,
  onEditPost,
  onDuplicatePost,
  onDeletePost,
}) {
  const isToday = isSameDay(date, new Date())
  const dayName = format(date, 'EEEE').toLowerCase()
  const optimalTimesForDay = optimalTimes[dayName] || []
  const [showTimeSlots, setShowTimeSlots] = useState(false)

  const { setNodeRef, isOver } = useDroppable({
    id: format(date, 'yyyy-MM-dd'),
  })

  // Group posts by time for better visualization
  const groupedPosts = useMemo(() => {
    const groups = {}
    posts.forEach((post) => {
      const hour = post.time.split(':')[0]
      if (!groups[hour]) groups[hour] = []
      groups[hour].push(post)
    })
    return groups
  }, [posts])

  const timeSlots = Array.from({ length: 24 }, (_, i) => {
    const hour = i.toString().padStart(2, '0')
    return {
      hour,
      time: `${hour}:00`,
      posts: groupedPosts[hour] || [],
      isOptimal: optimalTimesForDay.some((t) => t.hour === i && t.score >= 80),
    }
  })

  return (
    <div
      ref={setNodeRef}
      className={`min-h-48 p-2 border-r border-b border-gray-200 hover:bg-gray-50 relative transition-colors ${
        isToday ? 'bg-blue-50' : ''
      } ${isOver ? 'bg-green-50 ring-2 ring-green-400' : ''}`}
    >
      {/* Day header */}
      <div className="sticky top-0 bg-white z-10 pb-2 mb-2 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div
            className={`text-sm font-medium ${
              isToday ? 'text-blue-600' : 'text-gray-900'
            }`}
          >
            {isToday ? (
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white text-xs">
                {day}
              </span>
            ) : (
              day
            )}
          </div>

          <div className="flex items-center space-x-1">
            {/* Toggle time slots view */}
            <button
              onClick={() => setShowTimeSlots(!showTimeSlots)}
              className={`p-1 rounded text-xs transition-colors ${
                showTimeSlots
                  ? 'bg-blue-100 text-blue-600'
                  : 'hover:bg-gray-200 text-gray-500'
              }`}
              title="Toggle time slots"
            >
              <ClockIcon className="h-3 w-3" />
            </button>

            {/* Add post button */}
            <button
              onClick={() => onAddPost(date)}
              className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
              title="Add post"
            >
              <PlusIcon className="h-3 w-3" />
            </button>
          </div>
        </div>

        {/* Post count and optimal indicators */}
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-gray-500">
            {posts.length} post{posts.length !== 1 ? 's' : ''}
          </span>
          <div className="flex space-x-1">
            {optimalTimesForDay.slice(0, 3).map((time, index) => (
              <div
                key={index}
                className={`w-1.5 h-1.5 rounded-full ${
                  time.score >= 90
                    ? 'bg-red-400'
                    : time.score >= 80
                      ? 'bg-orange-400'
                      : 'bg-gray-300'
                }`}
                title={`Optimal: ${time.hour}:00 (${time.score}% engagement)`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Posts display */}
      <div className="space-y-1 max-h-96 overflow-y-auto">
        {showTimeSlots ? (
          // Time slot view
          <div className="space-y-2">
            {timeSlots
              .filter((slot) => slot.posts.length > 0 || slot.isOptimal)
              .map((slot) => (
                <div
                  key={slot.hour}
                  className={`border rounded p-2 ${
                    slot.isOptimal
                      ? 'border-orange-200 bg-orange-50'
                      : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-700">
                      {slot.time}
                    </span>
                    {slot.isOptimal && (
                      <ChartBarIcon
                        className="h-3 w-3 text-orange-500"
                        title="Optimal time"
                      />
                    )}
                  </div>
                  <SortableContext
                    items={slot.posts.map((p) => p.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    {slot.posts.map((post) => (
                      <DraggablePostItem
                        key={post.id}
                        post={post}
                        isSelected={selectedPosts.includes(post.id)}
                        onSelect={onSelectPost}
                        onEdit={onEditPost}
                        onDuplicate={onDuplicatePost}
                        onDelete={onDeletePost}
                      />
                    ))}
                  </SortableContext>
                  {slot.posts.length === 0 && slot.isOptimal && (
                    <button
                      onClick={() => onAddPost(date, slot.time)}
                      className="w-full text-xs text-gray-500 hover:text-orange-600 py-1 border-2 border-dashed border-gray-300 hover:border-orange-300 rounded transition-colors"
                    >
                      Schedule for {slot.time}
                    </button>
                  )}
                </div>
              ))}
          </div>
        ) : (
          // Regular list view
          <SortableContext
            items={posts.map((p) => p.id)}
            strategy={verticalListSortingStrategy}
          >
            {posts.map((post) => (
              <DraggablePostItem
                key={post.id}
                post={post}
                isSelected={selectedPosts.includes(post.id)}
                onSelect={onSelectPost}
                onEdit={onEditPost}
                onDuplicate={onDuplicatePost}
                onDelete={onDeletePost}
              />
            ))}
          </SortableContext>
        )}

        {posts.length === 0 && (
          <div
            onClick={() => onAddPost(date)}
            className="flex items-center justify-center h-20 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 cursor-pointer transition-colors"
          >
            <div className="text-center">
              <PlusIcon className="h-6 w-6 text-gray-400 mx-auto mb-1" />
              <span className="text-xs text-gray-500">Add post</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
})

const DragDropCalendar = React.memo(function DragDropCalendar({
  posts = [],
  onPostMove,
  onAddPost,
  onEditPost,
  onDuplicatePost,
  onDeletePost,
}) {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [activeId, setActiveId] = useState(null)
  const [selectedPosts, setSelectedPosts] = useState([])
  const [bulkActionsOpen, setBulkActionsOpen] = useState(false)
  const [announcement, setAnnouncement] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Generate week days for the current week
  const weekStart = startOfWeek(currentDate)
  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  }, [weekStart])

  const getPostsForDate = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd')
    return posts.filter((post) => post.date === dateStr)
  }

  const navigateWeek = (direction) => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() + direction * 7)
    setCurrentDate(newDate)
  }

  const handleDragStart = (event) => {
    setActiveId(event.active.id)

    const post = posts.find((p) => p.id === event.active.id)
    const announcement = `Picked up post: ${post?.title || 'Untitled'}. Navigate to a new date and press Space to drop.`
    setAnnouncement(announcement)

    // Clear announcement after a delay
    setTimeout(() => setAnnouncement(''), 2000)
  }

  const handleDragEnd = (event) => {
    const { active, over } = event

    if (active.id !== over?.id && over) {
      // Handle post reordering or moving between days
      const activePost = posts.find((p) => p.id === active.id)
      if (activePost && onPostMove) {
        // If dropping on a date (day cell), move to that date
        if (over.id.includes('-')) {
          const targetDate = over.id
          const targetDateFormatted = format(
            new Date(targetDate),
            'EEEE, MMMM do'
          )
          setAnnouncement(
            `Post "${activePost.title || 'Untitled'}" moved to ${targetDateFormatted}`
          )
          onPostMove(activePost, targetDate)
        } else {
          // If dropping on another post, reorder
          setAnnouncement(`Post "${activePost.title || 'Untitled'}" reordered`)
          onPostMove(activePost, over.id)
        }
      }
    } else if (active.id === over?.id) {
      setAnnouncement('Post dropped in same location - no change made')
    } else {
      setAnnouncement(
        'Post dropped in invalid location - returned to original position'
      )
    }

    setActiveId(null)

    // Clear announcement after a delay
    setTimeout(() => setAnnouncement(''), 3000)
  }

  const handleAddPost = (date, time = null) => {
    if (onAddPost) {
      onAddPost(format(date, 'yyyy-MM-dd'), time)
    }
  }

  // Selection handlers
  const handleSelectPost = useCallback((postId, isSelected) => {
    setSelectedPosts((prev) =>
      isSelected ? [...prev, postId] : prev.filter((id) => id !== postId)
    )
  }, [])

  const handleSelectAll = useCallback(() => {
    const visiblePostIds = weekDays.flatMap((date) =>
      getPostsForDate(date).map((post) => post.id)
    )
    setSelectedPosts(visiblePostIds)
  }, [weekDays, posts])

  const handleDeselectAll = useCallback(() => {
    setSelectedPosts([])
  }, [])

  // Bulk action handlers
  const handleBulkDelete = useCallback(() => {
    if (selectedPosts.length > 0 && onDeletePost) {
      selectedPosts.forEach((postId) => onDeletePost(postId))
      setSelectedPosts([])
      setBulkActionsOpen(false)
    }
  }, [selectedPosts, onDeletePost])

  const handleBulkReschedule = useCallback(() => {
    // This would open a bulk reschedule modal
    logDebug('Bulk reschedule:', selectedPosts)
    setBulkActionsOpen(false)
  }, [selectedPosts])

  // Enhanced edit handlers
  const handleEditPost = useCallback(
    (post) => {
      if (onEditPost) {
        onEditPost(post)
      }
    },
    [onEditPost]
  )

  const handleDuplicatePost = useCallback(
    (post) => {
      if (onDuplicatePost) {
        onDuplicatePost(post)
      }
    },
    [onDuplicatePost]
  )

  const handleDeletePost = useCallback(
    (postId) => {
      if (onDeletePost) {
        onDeletePost(postId)
      }
    },
    [onDeletePost]
  )

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={rectIntersection}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="space-y-6">
        {/* Screen Reader Announcements */}
        <div
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
          role="status"
        >
          {announcement}
        </div>

        {/* Accessibility Instructions */}
        <DragDropInstructions type="calendar" compact={true} />

        {/* Enhanced Calendar Header with Bulk Actions */}
        <div className="flex items-center justify-end">
          <div className="flex items-center space-x-2">
            {/* Bulk Actions */}
            {selectedPosts.length > 0 && (
              <div className="flex items-center space-x-2 mr-4">
                <span className="text-sm text-gray-600">
                  {selectedPosts.length} selected
                </span>
                <div className="relative">
                  <button
                    onClick={() => setBulkActionsOpen(!bulkActionsOpen)}
                    className="p-2 rounded-md border border-gray-300 bg-white hover:bg-gray-50"
                    title="Bulk actions"
                  >
                    <EllipsisHorizontalIcon className="h-5 w-5" />
                  </button>
                  {bulkActionsOpen && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border z-10">
                      <div className="py-1">
                        <button
                          onClick={handleBulkReschedule}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          <ArrowsRightLeftIcon className="h-4 w-4 mr-2" />
                          Reschedule Selected
                        </button>
                        <button
                          onClick={handleBulkDelete}
                          className="flex items-center w-full px-4 py-2 text-sm text-red-700 hover:bg-red-50"
                        >
                          <TrashIcon className="h-4 w-4 mr-2" />
                          Delete Selected
                        </button>
                        <div className="border-t border-gray-100 my-1"></div>
                        <button
                          onClick={handleSelectAll}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          <CheckIcon className="h-4 w-4 mr-2" />
                          Select All Week
                        </button>
                        <button
                          onClick={handleDeselectAll}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          <XMarkIcon className="h-4 w-4 mr-2" />
                          Deselect All
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Calendar Grid */}
        <div className="bg-white rounded-lg shadow">
          {/* Day headers */}
          <div className="grid grid-cols-7 border-b border-gray-200">
            {weekDays.map((date, index) => (
              <div key={format(date, 'yyyy-MM-dd')} className="p-4 text-center">
                <div className="text-sm font-medium text-gray-500">
                  {dayNames[index]}
                </div>
                <div
                  className={`text-lg font-semibold mt-1 ${
                    isSameDay(date, new Date())
                      ? 'text-blue-600'
                      : 'text-gray-900'
                  }`}
                >
                  {format(date, 'd')}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {getPostsForDate(date).length} posts
                </div>
              </div>
            ))}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7">
            {weekDays.map((date) => (
              <DroppableDay
                key={format(date, 'yyyy-MM-dd')}
                day={format(date, 'd')}
                date={date}
                posts={getPostsForDate(date)}
                currentDate={currentDate}
                onAddPost={handleAddPost}
                selectedPosts={selectedPosts}
                onSelectPost={handleSelectPost}
                onEditPost={handleEditPost}
                onDuplicatePost={handleDuplicatePost}
                onDeletePost={handleDeletePost}
              />
            ))}
          </div>
        </div>

        {/* Enhanced Legend and Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">
              Optimal Posting Times
            </h4>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                <span className="text-xs text-gray-600">
                  Peak Time (90%+ engagement)
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-orange-400"></div>
                <span className="text-xs text-gray-600">
                  Good Time (80-89% engagement)
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-gray-300"></div>
                <span className="text-xs text-gray-600">
                  Average Time (below 80%)
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">
              Week Statistics
            </h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Total posts:</span>
                <span className="font-medium ml-1">{posts.length}</span>
              </div>
              <div>
                <span className="text-gray-600">Scheduled:</span>
                <span className="font-medium ml-1 text-green-600">
                  {posts.filter((p) => p.status === 'scheduled').length}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Drafts:</span>
                <span className="font-medium ml-1 text-yellow-600">
                  {posts.filter((p) => p.status === 'draft').length}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Peak times:</span>
                <span className="font-medium ml-1">
                  {
                    posts.filter((p) => {
                      const postDate = parseISO(p.date + 'T' + p.time)
                      const dayName = [
                        'sunday',
                        'monday',
                        'tuesday',
                        'wednesday',
                        'thursday',
                        'friday',
                        'saturday',
                      ][postDate.getDay()]
                      const dayOptimal = optimalTimes[dayName] || []
                      const closest = dayOptimal.reduce(
                        (prev, curr) =>
                          Math.abs(curr.hour - postDate.getHours()) <
                          Math.abs(prev.hour - postDate.getHours())
                            ? curr
                            : prev,
                        { hour: 12, score: 50 }
                      )
                      return closest.score >= 90
                    }).length
                  }
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Drag overlay for active item */}
      <DragOverlay>
        {activeId ? (
          <div className="transform rotate-3 scale-105 opacity-90">
            <DraggablePostItem
              post={posts.find((p) => p.id === activeId)}
              isDragging
              isSelected={selectedPosts.includes(activeId)}
              onSelect={() => {}}
              onEdit={() => {}}
              onDuplicate={() => {}}
              onDelete={() => {}}
            />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
})

export default DragDropCalendar
