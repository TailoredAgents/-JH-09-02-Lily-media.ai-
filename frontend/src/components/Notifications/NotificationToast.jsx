import { useState, useEffect, useRef } from 'react'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon,
  XMarkIcon,
  ArrowPathIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'

const NotificationToast = ({ notification, onDismiss, onRetry }) => {
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryCount, setRetryCount] = useState(notification.retryCount || 0)
  const timeoutRef = useRef(null)
  const progressRef = useRef(null)

  useEffect(() => {
    // Animate in
    setIsVisible(true)

    // Auto-dismiss after duration
    if (notification.duration && !notification.persistent) {
      timeoutRef.current = setTimeout(() => {
        handleDismiss()
      }, notification.duration)
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [notification.duration, notification.persistent])

  const handleDismiss = () => {
    // Clear any running timers
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    
    setIsExiting(true)
    setTimeout(() => {
      onDismiss(notification.id)
    }, 300) // Match animation duration
  }

  const handleRetry = async () => {
    if (!notification.retryAction || isRetrying || retryCount >= (notification.maxRetries || 3)) {
      return
    }

    setIsRetrying(true)
    
    try {
      await notification.retryAction()
      // If retry succeeds, dismiss the toast
      handleDismiss()
    } catch (error) {
      // If retry fails, increment count and keep showing
      setRetryCount(prev => prev + 1)
      setIsRetrying(false)
      
      // Show retry failed feedback
      if (onRetry) {
        onRetry(notification.id, error)
      }
    }
  }

  const pauseTimer = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
  }

  const resumeTimer = () => {
    if (notification.duration && !notification.persistent && !isRetrying) {
      timeoutRef.current = setTimeout(() => {
        handleDismiss()
      }, notification.duration)
    }
  }

  const getIcon = () => {
    const iconClasses = "h-6 w-6"
    
    switch (notification.type) {
      case 'success':
        return <CheckCircleIcon className={`${iconClasses} text-green-400`} />
      case 'error':
        return <XCircleIcon className={`${iconClasses} text-red-400`} />
      case 'warning':
        return <ExclamationTriangleIcon className={`${iconClasses} text-yellow-400`} />
      case 'info':
      default:
        return <InformationCircleIcon className={`${iconClasses} text-blue-400`} />
    }
  }

  const getBackgroundColor = () => {
    switch (notification.type) {
      case 'success':
        return 'bg-green-50 border-green-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200'
    }
  }

  const canRetry = notification.retryAction && retryCount < (notification.maxRetries || 3)
  const hasRetryFailed = retryCount > 0

  return (
    <div
      className={`
        max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden
        transform transition-all duration-300 ease-in-out
        ${isVisible && !isExiting ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        ${getBackgroundColor()}
      `}
      onMouseEnter={pauseTimer}
      onMouseLeave={resumeTimer}
      onFocus={pauseTimer}
      onBlur={resumeTimer}
      role="alert"
      aria-live={notification.type === 'error' ? 'assertive' : 'polite'}
      aria-labelledby={`toast-title-${notification.id}`}
      aria-describedby={`toast-message-${notification.id}`}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {isRetrying ? (
              <ArrowPathIcon className="h-6 w-6 text-blue-400 animate-spin" />
            ) : (
              getIcon()
            )}
          </div>
          <div className="ml-3 w-0 flex-1 pt-0.5">
            <p 
              id={`toast-title-${notification.id}`}
              className="text-sm font-medium text-gray-900"
            >
              {isRetrying ? 'Retrying...' : notification.title}
            </p>
            <p 
              id={`toast-message-${notification.id}`}
              className="mt-1 text-sm text-gray-500"
            >
              {isRetrying ? 'Please wait while we retry the operation...' : notification.message}
            </p>
            
            {/* Retry attempt indicator */}
            {hasRetryFailed && !isRetrying && (
              <p className="mt-1 text-xs text-orange-600">
                Retry attempt {retryCount} of {notification.maxRetries || 3}
              </p>
            )}

            {/* Action buttons */}
            <div className="mt-3 flex flex-wrap gap-2">
              {notification.action && !isRetrying && (
                <button
                  onClick={notification.action.onClick}
                  className="text-sm font-medium text-blue-600 hover:text-blue-500 focus:outline-none focus:underline"
                  type="button"
                >
                  {notification.action.label}
                </button>
              )}
              
              {canRetry && !isRetrying && (
                <button
                  onClick={handleRetry}
                  className="inline-flex items-center text-sm font-medium text-orange-600 hover:text-orange-500 focus:outline-none focus:underline"
                  type="button"
                  disabled={isRetrying}
                  aria-label={`Retry operation (${retryCount} of ${notification.maxRetries || 3} attempts used)`}
                >
                  <ArrowPathIcon className="w-4 h-4 mr-1" aria-hidden="true" />
                  Retry
                </button>
              )}
            </div>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 p-1"
              onClick={handleDismiss}
              disabled={isRetrying}
              aria-label="Close notification"
              type="button"
            >
              <span className="sr-only">Close notification</span>
              <XMarkIcon className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Progress bar for timed notifications */}
      {notification.duration && !notification.persistent && (
        <div className="h-1 bg-gray-200">
          <div
            className={`h-full transition-all ease-linear ${
              notification.type === 'success' ? 'bg-green-400' :
              notification.type === 'error' ? 'bg-red-400' :
              notification.type === 'warning' ? 'bg-yellow-400' :
              'bg-blue-400'
            }`}
            style={{
              animation: `shrink ${notification.duration}ms linear`,
              animationFillMode: 'forwards'
            }}
          />
        </div>
      )}
      
      <style jsx>{`
        @keyframes shrink {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  )
}

export default NotificationToast