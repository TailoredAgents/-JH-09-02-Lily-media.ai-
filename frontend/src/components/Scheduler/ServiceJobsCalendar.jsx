import React, { useState, useMemo, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  useDroppable,
} from '@dnd-kit/core'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { format, addDays, startOfWeek, isSameDay, parseISO } from 'date-fns'
import {
  ClockIcon,
  MapPinIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import WeatherIndicator from './WeatherIndicator'
import { debug as logDebug } from '../../utils/logger.js'

/**
 * PW-FE-REPLACE-001: Service Jobs Calendar with drag-and-drop
 *
 * Displays service jobs in a weekly calendar format with:
 * - Drag-and-drop rescheduling
 * - Status-based color coding
 * - Weather indicators
 * - Duration-based sizing
 */

// Job status color mapping
const jobStatusColors = {
  scheduled: {
    bg: 'bg-blue-100 hover:bg-blue-200',
    border: 'border-blue-200',
    text: 'text-blue-900',
    dot: 'bg-blue-500',
    icon: CheckCircleIcon,
  },
  in_progress: {
    bg: 'bg-yellow-100 hover:bg-yellow-200',
    border: 'border-yellow-200',
    text: 'text-yellow-900',
    dot: 'bg-yellow-500',
    icon: ClockIcon,
  },
  completed: {
    bg: 'bg-green-100 hover:bg-green-200',
    border: 'border-green-200',
    text: 'text-green-900',
    dot: 'bg-green-500',
    icon: CheckCircleIcon,
  },
  canceled: {
    bg: 'bg-red-100 hover:bg-red-200',
    border: 'border-red-200',
    text: 'text-red-900',
    dot: 'bg-red-500',
    icon: XCircleIcon,
  },
  rescheduled: {
    bg: 'bg-orange-100 hover:bg-orange-200',
    border: 'border-orange-200',
    text: 'text-orange-900',
    dot: 'bg-orange-500',
    icon: PauseIcon,
  },
}

// Service type color mapping
const serviceTypeColors = {
  pressure_washing: 'border-l-blue-500',
  soft_wash: 'border-l-purple-500',
  roof_cleaning: 'border-l-red-500',
  gutter_cleaning: 'border-l-green-500',
  deck_cleaning: 'border-l-yellow-500',
  driveway_cleaning: 'border-l-indigo-500',
  house_washing: 'border-l-pink-500',
  default: 'border-l-gray-500',
}

// Draggable Job Item Component
const DraggableJobItem = ({ job, weatherRisk = false, onWeatherCheck }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: job.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const statusConfig = jobStatusColors[job.status] || jobStatusColors.scheduled
  const serviceColor =
    serviceTypeColors[job.service_type] || serviceTypeColors.default
  const StatusIcon = statusConfig.icon

  const formatTime = (dateTimeString) => {
    if (!dateTimeString) return ''
    return format(parseISO(dateTimeString), 'h:mm a')
  }

  const formatDuration = (minutes) => {
    if (!minutes) return ''
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours > 0 && mins > 0) {
      return `${hours}h ${mins}m`
    } else if (hours > 0) {
      return `${hours}h`
    } else {
      return `${mins}m`
    }
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        relative p-3 mb-2 rounded-lg border-2 border-l-4 cursor-move shadow-sm
        ${statusConfig.bg} ${statusConfig.border} ${serviceColor}
        ${isDragging ? 'opacity-50 shadow-lg' : ''}
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        transition-all duration-200
      `}
      tabIndex={0}
      role="button"
      aria-label={`Job: ${job.service_type} at ${job.address}, scheduled for ${formatTime(job.scheduled_for)}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          // Handle keyboard-based drag initiation if needed
        }
      }}
    >
      {/* Weather Indicator */}
      {weatherRisk && (
        <div className="absolute -top-1 -right-1">
          <WeatherIndicator
            jobId={job.id}
            isRisky={true}
            onClick={() => onWeatherCheck && onWeatherCheck(job.id)}
          />
        </div>
      )}

      {/* Job Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <StatusIcon className={`h-4 w-4 ${statusConfig.text}`} />
          <span className={`text-sm font-medium ${statusConfig.text}`}>
            {job.service_type.replace('_', ' ').toUpperCase()}
          </span>
        </div>
        <div className="flex items-center space-x-1 text-xs text-gray-600">
          <ClockIcon className="h-3 w-3" />
          <span>{formatTime(job.scheduled_for)}</span>
          {job.duration_minutes && (
            <>
              <span>•</span>
              <span>{formatDuration(job.duration_minutes)}</span>
            </>
          )}
        </div>
      </div>

      {/* Job Address */}
      <div className="flex items-center space-x-1 mb-2">
        <MapPinIcon className="h-3 w-3 text-gray-500 flex-shrink-0" />
        <span className="text-xs text-gray-600 truncate" title={job.address}>
          {job.address}
        </span>
      </div>

      {/* Job Details */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${statusConfig.dot}`} />
          <span className={`text-xs font-medium ${statusConfig.text}`}>
            {job.status.replace('_', ' ').toUpperCase()}
          </span>
        </div>
        {job.estimated_cost && (
          <span className="text-xs font-medium text-gray-700">
            ${parseFloat(job.estimated_cost).toFixed(0)}
          </span>
        )}
      </div>
    </div>
  )
}

// Droppable Day Column Component
const DroppableDay = ({ date, jobs, children, isToday = false }) => {
  const { setNodeRef, isOver } = useDroppable({
    id: format(date, 'yyyy-MM-dd'),
  })

  return (
    <div
      ref={setNodeRef}
      className={`
        min-h-96 p-3 border-r border-gray-200 last:border-r-0
        ${isOver ? 'bg-blue-50' : ''}
        ${isToday ? 'bg-blue-25' : ''}
      `}
    >
      {/* Day Header */}
      <div className="mb-4 text-center">
        <div
          className={`text-sm font-medium ${isToday ? 'text-blue-600' : 'text-gray-700'}`}
        >
          {format(date, 'EEE')}
        </div>
        <div
          className={`text-lg ${isToday ? 'text-blue-600 font-bold' : 'text-gray-900'}`}
        >
          {format(date, 'd')}
        </div>
        {jobs.length > 0 && (
          <div className="text-xs text-gray-500 mt-1">
            {jobs.length} job{jobs.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Jobs List */}
      <div className="space-y-2">{children}</div>

      {/* Drop Indicator */}
      {isOver && (
        <div className="mt-4 p-2 border-2 border-dashed border-blue-300 rounded-lg bg-blue-50">
          <p className="text-xs text-blue-600 text-center font-medium">
            Drop job here to reschedule
          </p>
        </div>
      )}
    </div>
  )
}

// Main Service Jobs Calendar Component
const ServiceJobsCalendar = ({
  jobs = [],
  onJobMove,
  onWeatherCheck,
  weatherRisks = new Set(),
  currentWeek = new Date(),
}) => {
  const [activeJob, setActiveJob] = useState(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  )

  // Generate week dates starting from Sunday
  const weekDates = useMemo(() => {
    const start = startOfWeek(currentWeek)
    return Array.from({ length: 7 }, (_, i) => addDays(start, i))
  }, [currentWeek])

  // Group jobs by date
  const jobsByDate = useMemo(() => {
    const grouped = {}

    weekDates.forEach((date) => {
      const dateStr = format(date, 'yyyy-MM-dd')
      grouped[dateStr] = []
    })

    jobs.forEach((job) => {
      if (job.scheduled_for) {
        const jobDate = format(parseISO(job.scheduled_for), 'yyyy-MM-dd')
        if (grouped[jobDate]) {
          grouped[jobDate].push(job)
        }
      }
    })

    // Sort jobs by scheduled time within each day
    Object.keys(grouped).forEach((date) => {
      grouped[date].sort((a, b) => {
        const timeA = a.scheduled_for ? new Date(a.scheduled_for) : new Date()
        const timeB = b.scheduled_for ? new Date(b.scheduled_for) : new Date()
        return timeA - timeB
      })
    })

    return grouped
  }, [jobs, weekDates])

  const handleDragStart = useCallback(
    (event) => {
      const { active } = event
      setActiveJob(jobs.find((job) => job.id === active.id))
      logDebug('Drag started for job:', active.id)
    },
    [jobs]
  )

  const handleDragEnd = useCallback(
    (event) => {
      const { active, over } = event
      setActiveJob(null)

      if (!over) {
        logDebug('Drag ended without drop target')
        return
      }

      const jobId = active.id
      const targetDate = over.id // This will be the date string like '2024-01-15'

      logDebug('Job drag ended:', { jobId, targetDate })

      if (onJobMove) {
        onJobMove(jobId, targetDate)
      }
    },
    [onJobMove]
  )

  const handleDragCancel = useCallback(() => {
    setActiveJob(null)
  }, [])

  const today = new Date()

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Calendar Header */}
      <div className="bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">
            Week of {format(weekDates[0], 'MMM d')} -{' '}
            {format(weekDates[6], 'MMM d, yyyy')}
          </h3>
          <div className="flex items-center space-x-4">
            {/* Status Legend */}
            <div className="flex items-center space-x-3 text-xs">
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                <span className="text-gray-600">Scheduled</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                <span className="text-gray-600">In Progress</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-gray-600">Completed</span>
              </div>
              <div className="flex items-center space-x-1">
                <ExclamationTriangleIcon className="h-3 w-3 text-amber-500" />
                <span className="text-gray-600">Weather Risk</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Drag and Drop Context */}
      <DndContext
        sensors={sensors}
        collisionDetection={pointerWithin}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        {/* Calendar Grid */}
        <div className="grid grid-cols-7">
          {weekDates.map((date) => {
            const dateStr = format(date, 'yyyy-MM-dd')
            const dayJobs = jobsByDate[dateStr] || []
            const isToday = isSameDay(date, today)

            return (
              <DroppableDay
                key={dateStr}
                date={date}
                jobs={dayJobs}
                isToday={isToday}
              >
                {dayJobs.map((job) => (
                  <DraggableJobItem
                    key={job.id}
                    job={job}
                    weatherRisk={weatherRisks.has(job.id)}
                    onWeatherCheck={onWeatherCheck}
                  />
                ))}
              </DroppableDay>
            )
          })}
        </div>

        {/* Drag Overlay */}
        <DragOverlay>
          {activeJob ? (
            <DraggableJobItem
              job={activeJob}
              weatherRisk={weatherRisks.has(activeJob.id)}
            />
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  )
}

export default ServiceJobsCalendar
