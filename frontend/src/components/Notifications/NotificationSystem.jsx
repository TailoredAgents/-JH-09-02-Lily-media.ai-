import { useState, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { error as logError } from '../../utils/logger.js'
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  InformationCircleIcon, 
  XCircleIcon,
  XMarkIcon,
  BellIcon
} from '@heroicons/react/24/outline'
import { useEnhancedApi } from '../../hooks/useEnhancedApi'
import { useNotifications } from '../../hooks/useNotifications'
import { useAuth } from '../../contexts/AuthContext'
import { useSchemaStatus } from '../../hooks/useSchemaStatus'

// Toast notification component
function Toast({ notification, onClose }) {
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    // Animate in
    const timer = setTimeout(() => setIsVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    // Auto-dismiss after duration
    if (notification.duration && notification.duration > 0) {
      const timer = setTimeout(() => {
        handleClose()
      }, notification.duration)
      return () => clearTimeout(timer)
    }
  }, [notification.duration])

  const handleClose = useCallback(() => {
    setIsExiting(true)
    setTimeout(() => {
      onClose(notification.id)
    }, 300) // Match animation duration
  }, [notification.id, onClose])

  const getIcon = () => {
    switch (notification.type) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-400" />
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-400" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
      case 'info':
      default:
        return <InformationCircleIcon className="h-5 w-5 text-blue-400" />
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

  return (
    <div
      className={`max-w-sm w-full ${getBackgroundColor()} border rounded-lg shadow-lg pointer-events-auto transform transition-all duration-300 ease-in-out ${
        isVisible && !isExiting 
          ? 'translate-x-0 opacity-100' 
          : 'translate-x-full opacity-0'
      }`}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {getIcon()}
          </div>
          <div className="ml-3 w-0 flex-1">
            {notification.title && (
              <p className="text-sm font-medium text-gray-900">
                {notification.title}
              </p>
            )}
            <p className={`text-sm text-gray-500 ${notification.title ? 'mt-1' : ''}`}>
              {notification.message}
            </p>
            {notification.action && (
              <div className="mt-3">
                <button
                  onClick={notification.action.onClick}
                  className="text-sm font-medium text-blue-600 hover:text-blue-500"
                >
                  {notification.action.label}
                </button>
              </div>
            )}
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={handleClose}
              className="rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// In-app notification dropdown component
function NotificationDropdown({ notifications, onMarkRead, onMarkAllRead, onClose }) {
  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="absolute right-0 mt-2 w-80 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
      <div className="py-1 max-h-96 overflow-y-auto">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900">
              Notifications {unreadCount > 0 && (
                <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {unreadCount} new
                </span>
              )}
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={onMarkAllRead}
                className="text-xs text-blue-600 hover:text-blue-500"
              >
                Mark all read
              </button>
            )}
          </div>
        </div>

        {/* Notifications list */}
        {notifications.length === 0 ? (
          <div className="px-4 py-6 text-center text-gray-500">
            <BellIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No notifications</h3>
            <p className="mt-1 text-sm text-gray-500">You're all caught up!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {notifications.slice(0, 10).map((notification) => (
              <div
                key={notification.id}
                className={`px-4 py-3 hover:bg-gray-50 cursor-pointer ${
                  !notification.read ? 'bg-blue-50' : ''
                }`}
                onClick={() => onMarkRead(notification.id)}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    {notification.type === 'goal_milestone' && (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    )}
                    {notification.type === 'content_published' && (
                      <InformationCircleIcon className="h-5 w-5 text-blue-500" />
                    )}
                    {notification.type === 'workflow_completed' && (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    )}
                    {notification.type === 'system_alert' && (
                      <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {notification.title}
                    </p>
                    <p className="text-sm text-gray-500 truncate">
                      {notification.message}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </div>
                  {!notification.read && (
                    <div className="flex-shrink-0">
                      <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {notifications.length > 10 && (
          <div className="px-4 py-3 border-t border-gray-200">
            <button
              onClick={onClose}
              className="text-sm text-blue-600 hover:text-blue-500"
            >
              View all notifications
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Main notification system component
export default function NotificationSystem() {
  const [toasts, setToasts] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [toastQueue, setToastQueue] = useState([])
  const MAX_VISIBLE_TOASTS = 5
  const MAX_QUEUE_SIZE = 20
  
  const { api, connectionStatus } = useEnhancedApi()
  const { showToast } = useNotifications()
  const { isAuthenticated } = useAuth()
  const { shouldPoll, getPollingInterval, getStatusMessage } = useSchemaStatus()

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      const response = await api.notifications.getAll()
      // Extract notifications array from response object - API returns {notifications: [], total: number}
      const fetchedNotifications = response?.notifications || []
      setNotifications(Array.isArray(fetchedNotifications) ? fetchedNotifications : [])
    } catch (error) {
      logError('Failed to fetch notifications:', error)
      setNotifications([]) // Ensure it's always an array on error
    }
  }, [api])

  // Poll for new notifications with schema-aware throttling
  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([]) // Clear notifications when not authenticated
      return
    }
    
    // Only start polling if schema allows it
    if (!shouldPoll()) {
      console.info('NotificationSystem: Polling disabled due to database schema issues')
      setNotifications([])
      return
    }
    
    // Initial fetch
    fetchNotifications()
    
    // Set up polling with dynamic interval based on schema health
    const pollingInterval = getPollingInterval(30000, 300000) // 30s normal, 5min degraded
    console.info(`NotificationSystem: Polling every ${pollingInterval / 1000}s`)
    
    const interval = setInterval(fetchNotifications, pollingInterval)
    return () => clearInterval(interval)
  }, [fetchNotifications, isAuthenticated, shouldPoll, getPollingInterval])

  // Process toast queue
  const processToastQueue = useCallback(() => {
    setToasts(prev => {
      if (prev.length < MAX_VISIBLE_TOASTS && toastQueue.length > 0) {
        const nextToast = toastQueue[0]
        setToastQueue(queue => queue.slice(1))
        return [...prev, nextToast]
      }
      return prev
    })
  }, [toastQueue])

  // Process queue when toasts change
  useEffect(() => {
    processToastQueue()
  }, [processToastQueue, toasts.length])

  // Add toast notification with queue management
  const addToast = useCallback((notification) => {
    const id = Math.random().toString(36).substr(2, 9)
    const timestamp = Date.now()
    
    const toast = {
      id,
      type: notification.type || 'info',
      title: notification.title,
      message: notification.message,
      duration: notification.duration || 5000,
      action: notification.action,
      retryAction: notification.retryAction,
      maxRetries: notification.maxRetries || 3,
      retryCount: 0,
      priority: notification.priority || 'normal', // 'high', 'normal', 'low'
      persistent: notification.persistent || false,
      timestamp
    }
    
    // Check for duplicate toasts (same title and message within 2 seconds)
    const isDuplicate = toasts.concat(toastQueue).some(existing => 
      existing.title === toast.title && 
      existing.message === toast.message && 
      timestamp - existing.timestamp < 2000
    )
    
    if (isDuplicate) {
      return // Don't add duplicate toasts
    }
    
    // Add directly if we have space, otherwise queue it
    setToasts(prev => {
      if (prev.length < MAX_VISIBLE_TOASTS) {
        return [...prev, toast]
      } else {
        // Add to queue with priority handling
        setToastQueue(queue => {
          const newQueue = [...queue, toast]
          
          // Sort by priority (high first) and limit queue size
          return newQueue
            .sort((a, b) => {
              const priorityOrder = { high: 3, normal: 2, low: 1 }
              return (priorityOrder[b.priority] || 2) - (priorityOrder[a.priority] || 2)
            })
            .slice(0, MAX_QUEUE_SIZE)
        })
        return prev
      }
    })
    
    // Also add to in-app notifications if it's an important notification
    if (notification.persistent) {
      const inAppNotification = {
        id,
        type: notification.notificationType || 'system_alert',
        title: notification.title,
        message: notification.message,
        read: false,
        created_at: new Date().toISOString()
      }
      setNotifications(prev => [inAppNotification, ...prev])
    }
  }, [toasts, toastQueue])

  // Remove toast notification
  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  // Handle retry failures
  const handleRetryFailure = useCallback((toastId, error) => {
    // Update the toast with retry failure information
    setToasts(prev => prev.map(toast => {
      if (toast.id === toastId) {
        return {
          ...toast,
          message: `${toast.message} (Retry failed: ${error.message || 'Unknown error'})`,
          type: 'error',
          duration: 8000 // Extend duration for error feedback
        }
      }
      return toast
    }))
  }, [])

  // Batch notification handling for multiple related notifications
  const addBatchToast = useCallback((notifications, options = {}) => {
    const batchId = Math.random().toString(36).substr(2, 9)
    const { title = 'Multiple Operations', priority = 'normal' } = options
    
    if (notifications.length === 1) {
      addToast(notifications[0])
      return
    }

    const successCount = notifications.filter(n => n.type === 'success').length
    const errorCount = notifications.filter(n => n.type === 'error').length
    const warningCount = notifications.filter(n => n.type === 'warning').length

    let batchType = 'info'
    let batchMessage = `Completed ${notifications.length} operations`

    if (errorCount > 0) {
      batchType = 'error'
      batchMessage = `${successCount} succeeded, ${errorCount} failed`
    } else if (warningCount > 0) {
      batchType = 'warning' 
      batchMessage = `${successCount} succeeded with ${warningCount} warnings`
    } else {
      batchType = 'success'
      batchMessage = `All ${successCount} operations completed successfully`
    }

    addToast({
      type: batchType,
      title,
      message: batchMessage,
      duration: 6000,
      priority,
      action: {
        label: 'View Details',
        onClick: () => {
          // Show detailed breakdown in a modal or expand the notification
          console.log('Batch details:', notifications)
        }
      }
    })
  }, [addToast])

  // Mark notification as read
  const markAsRead = useCallback(async (notificationId) => {
    try {
      await api.notifications.markRead(notificationId)
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      )
    } catch (error) {
      logError('Failed to mark notification as read:', error)
    }
  }, [api])

  // Mark all notifications as read
  const markAllAsRead = useCallback(async () => {
    try {
      await api.notifications.markAllRead()
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    } catch (error) {
      logError('Failed to mark all notifications as read:', error)
    }
  }, [api])

  // Listen for system events and create notifications
  useEffect(() => {
    const handleCreateNotification = (event) => {
      addToast(event.detail)
    }

    const handleGoalMilestone = (event) => {
      addToast({
        type: 'success',
        title: 'Goal Milestone Reached!',
        message: `You've reached a milestone in "${event.detail.goalTitle}"`,
        duration: 8000,
        persistent: true,
        notificationType: 'goal_milestone'
      })
    }

    const handleContentPublished = (event) => {
      addToast({
        type: 'info',
        title: 'Content Published',
        message: `"${event.detail.title}" has been published to ${event.detail.platform || 'platform'}`,
        duration: 5000,
        persistent: true,
        notificationType: 'content_published'
      })
    }

    const handleWorkflowCompleted = (event) => {
      addToast({
        type: 'success',
        title: 'Workflow Completed',
        message: `${event.detail.workflowType} workflow has finished successfully`,
        duration: 6000,
        persistent: true,
        notificationType: 'workflow_completed'
      })
    }

    const handleSystemAlert = (event) => {
      addToast({
        type: event.detail.severity === 'error' ? 'error' : 'warning',
        title: 'System Alert',
        message: event.detail.message,
        duration: event.detail.severity === 'error' ? 12000 : 8000,
        persistent: true,
        notificationType: 'system_alert'
      })
    }

    const handleApiError = (event) => {
      addToast({
        type: 'error',
        title: 'Connection Issue',
        message: event.detail.message || 'Having trouble connecting to the server',
        duration: 12000,
        priority: 'high',
        retryAction: event.detail.retryAction,
        maxRetries: event.detail.maxRetries || 3,
        action: {
          label: 'Dismiss',
          onClick: () => {} // Will be handled by toast dismiss
        }
      })
    }

    const handleBatchNotification = (event) => {
      addBatchToast(event.detail.notifications, event.detail.options)
    }

    // Listen for custom events
    window.addEventListener('createNotification', handleCreateNotification)
    window.addEventListener('goalMilestone', handleGoalMilestone)
    window.addEventListener('contentPublished', handleContentPublished)
    window.addEventListener('workflowCompleted', handleWorkflowCompleted)
    window.addEventListener('systemAlert', handleSystemAlert)
    window.addEventListener('apiError', handleApiError)
    window.addEventListener('createBatchNotification', handleBatchNotification)

    return () => {
      window.removeEventListener('createNotification', handleCreateNotification)
      window.removeEventListener('goalMilestone', handleGoalMilestone)
      window.removeEventListener('contentPublished', handleContentPublished)
      window.removeEventListener('workflowCompleted', handleWorkflowCompleted)
      window.removeEventListener('systemAlert', handleSystemAlert)
      window.removeEventListener('apiError', handleApiError)
      window.removeEventListener('createBatchNotification', handleBatchNotification)
    }
  }, [addToast])

  // Check for connection status changes
  useEffect(() => {
    if (connectionStatus === 'disconnected') {
      addToast({
        type: 'error',
        title: 'Connection Lost',
        message: 'Unable to connect to the server. Retrying...',
        duration: 0, // Persistent until connection restored
      })
    } else if (connectionStatus === 'connected') {
      // Remove connection error toasts when reconnected
      setToasts(prev => prev.filter(toast => 
        toast.title !== 'Connection Lost' && toast.title !== 'Connection Issue'
      ))
    }
  }, [connectionStatus, addToast])

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <>
      {/* Toast notifications container with accessibility */}
      {toasts.length > 0 && createPortal(
        <div 
          className="fixed inset-0 z-50 flex flex-col items-end justify-start p-6 space-y-4 pointer-events-none"
          aria-label="Notifications"
          role="region"
        >
          {toasts.map((toast) => (
            <Toast 
              key={toast.id} 
              notification={toast} 
              onDismiss={removeToast}
              onRetry={handleRetryFailure}
            />
          ))}
          
          {/* Queue indicator */}
          {toastQueue.length > 0 && (
            <div className="fixed bottom-6 right-6 bg-gray-800 text-white px-3 py-1 rounded-full text-xs pointer-events-auto">
              {toastQueue.length} more notification{toastQueue.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>,
        document.body
      )}

      {/* In-app notification bell (to be used in Layout) */}
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="relative p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md"
        >
          <BellIcon className="h-6 w-6" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 h-4 w-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {showDropdown && (
          <NotificationDropdown
            notifications={notifications}
            onMarkRead={markAsRead}
            onMarkAllRead={markAllAsRead}
            onClose={() => setShowDropdown(false)}
          />
        )}
      </div>
    </>
  )
}

// Export utility functions for creating notifications
export const createNotification = (notification) => {
  const event = new CustomEvent('createNotification', { detail: notification })
  window.dispatchEvent(event)
}

export const createGoalMilestoneNotification = (goalTitle) => {
  const event = new CustomEvent('goalMilestone', { detail: { goalTitle } })
  window.dispatchEvent(event)
}

export const createContentPublishedNotification = (title) => {
  const event = new CustomEvent('contentPublished', { detail: { title } })
  window.dispatchEvent(event)
}

export const createWorkflowCompletedNotification = (workflowType) => {
  const event = new CustomEvent('workflowCompleted', { detail: { workflowType } })
  window.dispatchEvent(event)
}

export const createSystemAlertNotification = (message, severity = 'warning') => {
  const event = new CustomEvent('systemAlert', { detail: { message, severity } })
  window.dispatchEvent(event)
}

// Enhanced notification creation with retry support
export const createRetryableNotification = (notification) => {
  const event = new CustomEvent('createNotification', { 
    detail: {
      ...notification,
      retryAction: notification.retryAction,
      maxRetries: notification.maxRetries || 3,
      priority: notification.priority || 'normal'
    }
  })
  window.dispatchEvent(event)
}

// Batch notification creation
export const createBatchNotification = (notifications, options = {}) => {
  const event = new CustomEvent('createBatchNotification', { 
    detail: { notifications, options }
  })
  window.dispatchEvent(event)
}

// API error with retry mechanism
export const createApiErrorNotification = (message, retryAction, maxRetries = 3) => {
  const event = new CustomEvent('apiError', { 
    detail: { 
      message,
      retryAction,
      maxRetries
    }
  })
  window.dispatchEvent(event)
}