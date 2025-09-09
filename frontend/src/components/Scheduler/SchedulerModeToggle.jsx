import React from 'react'
import {
  CalendarIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline'

/**
 * PW-FE-REPLACE-001: Dual-mode scheduler toggle component
 *
 * Toggles between Content Calendar and Service Jobs modes with accessibility support
 */
const SchedulerModeToggle = ({ mode, onModeChange, className = '' }) => {
  return (
    <div
      className={`flex items-center bg-gray-100 rounded-lg p-1 ${className}`}
    >
      <button
        type="button"
        onClick={() => onModeChange('content')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onModeChange('content')
          }
        }}
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          mode === 'content'
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
        }`}
        aria-pressed={mode === 'content'}
        aria-label="Switch to Content Calendar mode"
      >
        <CalendarIcon className="h-4 w-4" />
        <span>Content Calendar</span>
      </button>
      <button
        type="button"
        onClick={() => onModeChange('jobs')}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onModeChange('jobs')
          }
        }}
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          mode === 'jobs'
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
        }`}
        aria-pressed={mode === 'jobs'}
        aria-label="Switch to Service Jobs mode"
      >
        <WrenchScrewdriverIcon className="h-4 w-4" />
        <span>Service Jobs</span>
      </button>
    </div>
  )
}

export default SchedulerModeToggle
