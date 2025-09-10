import React, { useState } from 'react'
import {
  ExclamationTriangleIcon,
  CloudIcon,
  SunIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

/**
 * PW-FE-REPLACE-001: Weather risk indicator component
 *
 * Shows weather warning icon with tooltip for jobs at risk due to weather conditions
 */
const WeatherIndicator = ({
  jobId,
  isRisky = false,
  severity = 'moderate',
  reasons = [],
  onClick,
  className = '',
}) => {
  const [showTooltip, setShowTooltip] = useState(false)

  if (!isRisky) {
    return null
  }

  // Icon and color based on severity
  const getIconAndColor = () => {
    switch (severity) {
      case 'severe':
        return {
          icon: ExclamationTriangleIcon,
          bgColor: 'bg-red-500',
          textColor: 'text-red-500',
          hoverColor: 'hover:bg-red-600',
          pulseColor: 'animate-pulse',
        }
      case 'moderate':
        return {
          icon: ExclamationTriangleIcon,
          bgColor: 'bg-amber-500',
          textColor: 'text-amber-500',
          hoverColor: 'hover:bg-amber-600',
          pulseColor: '',
        }
      case 'light':
        return {
          icon: CloudIcon,
          bgColor: 'bg-yellow-500',
          textColor: 'text-yellow-500',
          hoverColor: 'hover:bg-yellow-600',
          pulseColor: '',
        }
      default:
        return {
          icon: InformationCircleIcon,
          bgColor: 'bg-blue-500',
          textColor: 'text-blue-500',
          hoverColor: 'hover:bg-blue-600',
          pulseColor: '',
        }
    }
  }

  const {
    icon: Icon,
    bgColor,
    textColor,
    hoverColor,
    pulseColor,
  } = getIconAndColor()

  const handleClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (onClick) {
      onClick(jobId)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick(e)
    }
  }

  return (
    <div
      className={`relative inline-block ${className}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
    >
      <button
        type="button"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={`
          p-1 rounded-full text-white shadow-lg transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2
          ${bgColor} ${hoverColor} ${pulseColor}
        `}
        aria-label={`Weather warning for job ${jobId}. Click for details.`}
        title="Weather conditions may affect this job"
      >
        <Icon className="h-3 w-3" />
      </button>

      {/* Tooltip */}
      {showTooltip && (
        <div
          className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 
                     bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-nowrap z-50
                     before:content-[''] before:absolute before:top-full before:left-1/2 
                     before:transform before:-translate-x-1/2 before:border-4 
                     before:border-transparent before:border-t-gray-900"
          role="tooltip"
        >
          <div className="font-medium mb-1">Weather Risk Detected</div>
          {reasons.length > 0 ? (
            <div className="space-y-1">
              {reasons.slice(0, 3).map((reason, index) => (
                <div key={index} className="text-gray-300">
                  • {reason}
                </div>
              ))}
              {reasons.length > 3 && (
                <div className="text-gray-400 italic">
                  +{reasons.length - 3} more reasons
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-300">
              Weather conditions may affect job scheduling
            </div>
          )}
          <div className="text-gray-400 mt-1 border-t border-gray-700 pt-1">
            Click for detailed forecast
          </div>
        </div>
      )}
    </div>
  )
}

export default WeatherIndicator
