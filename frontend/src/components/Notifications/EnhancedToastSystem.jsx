import React, { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  XMarkIcon,
  ArrowPathIcon,
  ClockIcon,
  PauseIcon,
  PlayIcon,
  WifiIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { useNotifications } from '../../hooks/useNotifications'
import { useAuth } from '../../contexts/AuthContext'

// Enhanced retry queue manager
class RetryQueueManager {
  constructor() {
    this.queue = []
    this.maxRetries = 3
    this.baseDelay = 1000
    this.maxDelay = 30000
    this.isProcessing = false
  }

  addToQueue(operation) {
    const queueItem = {
      id: Math.random().toString(36).substr(2, 9),
      operation,
      retryCount: 0,
      createdAt: Date.now(),
      lastAttemptAt: null,
      status: 'pending', // pending, retrying, failed, completed
      error: null,
    }

    this.queue.push(queueItem)
    this.processQueue()
    return queueItem.id
  }

  async processQueue() {
    if (this.isProcessing || this.queue.length === 0) return

    this.isProcessing = true

    const pendingItems = this.queue.filter(
      (item) => item.status === 'pending' && item.retryCount < this.maxRetries
    )

    for (const item of pendingItems) {
      try {
        item.status = 'retrying'
        item.lastAttemptAt = Date.now()

        const result = await item.operation.execute()

        item.status = 'completed'
        if (item.operation.onSuccess) {
          item.operation.onSuccess(result)
        }

        // Remove completed item from queue
        this.removeFromQueue(item.id)
      } catch (error) {
        item.retryCount++
        item.error = error

        if (item.retryCount >= this.maxRetries) {
          item.status = 'failed'
          if (item.operation.onFailure) {
            item.operation.onFailure(error, item.retryCount)
          }
        } else {
          item.status = 'pending'
          // Schedule next retry with exponential backoff
          const delay = Math.min(
            this.baseDelay * Math.pow(2, item.retryCount - 1),
            this.maxDelay
          )
          setTimeout(() => this.processQueue(), delay)
        }
      }
    }

    this.isProcessing = false
  }

  removeFromQueue(id) {
    this.queue = this.queue.filter((item) => item.id !== id)
  }

  getQueueStatus() {
    return {
      total: this.queue.length,
      pending: this.queue.filter((item) => item.status === 'pending').length,
      retrying: this.queue.filter((item) => item.status === 'retrying').length,
      failed: this.queue.filter((item) => item.status === 'failed').length,
    }
  }

  clearFailedItems() {
    this.queue = this.queue.filter((item) => item.status !== 'failed')
  }

  retryFailedItems() {
    this.queue.forEach((item) => {
      if (item.status === 'failed') {
        item.status = 'pending'
        item.retryCount = 0
        item.error = null
      }
    })
    this.processQueue()
  }
}

// Enhanced toast component with retry capabilities
function EnhancedToast({ notification, onClose, onRetry, retryQueue }) {
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [isRetrying, setIsRetrying] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (
      notification.duration &&
      notification.duration > 0 &&
      !notification.persistent
    ) {
      const timer = setTimeout(() => {
        handleClose()
      }, notification.duration)
      return () => clearTimeout(timer)
    }
  }, [notification.duration])

  // Progress simulation for operations
  useEffect(() => {
    if (notification.showProgress && isRetrying) {
      const interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return 90 // Don't complete until actual completion
          return prev + Math.random() * 10
        })
      }, 500)
      return () => clearInterval(interval)
    }
  }, [notification.showProgress, isRetrying])

  const handleClose = useCallback(() => {
    setIsExiting(true)
    setTimeout(() => {
      onClose(notification.id)
    }, 300)
  }, [notification.id, onClose])

  const handleRetry = useCallback(async () => {
    if (!notification.retryAction) return

    setIsRetrying(true)
    setProgress(0)

    try {
      await notification.retryAction()
      setRetryCount((prev) => prev + 1)

      // Show success feedback
      setProgress(100)
      setTimeout(() => {
        setIsRetrying(false)
        if (notification.autoCloseOnSuccess) {
          handleClose()
        }
      }, 1000)
    } catch (error) {
      setIsRetrying(false)
      setProgress(0)
      setRetryCount((prev) => prev + 1)

      // Could trigger another notification for the retry failure
      if (onRetry) {
        onRetry(notification.id, error)
      }
    }
  }, [notification, onRetry, handleClose])

  const getIcon = () => {
    if (isRetrying) {
      return <ArrowPathIcon className="h-5 w-5 text-blue-400 animate-spin" />
    }

    switch (notification.type) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-400" />
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-400" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
      case 'retry':
        return <ArrowPathIcon className="h-5 w-5 text-orange-400" />
      case 'offline':
        return <WifiIcon className="h-5 w-5 text-gray-400" />
      case 'info':
      default:
        return <InformationCircleIcon className="h-5 w-5 text-blue-400" />
    }
  }

  const getBackgroundColor = () => {
    if (notification.priority === 'high') {
      return 'bg-red-50 border-red-200 ring-2 ring-red-200'
    }

    switch (notification.type) {
      case 'success':
        return 'bg-green-50 border-green-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      case 'retry':
        return 'bg-orange-50 border-orange-200'
      case 'offline':
        return 'bg-gray-50 border-gray-200'
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
          <div className="flex-shrink-0">{getIcon()}</div>
          <div className="ml-3 w-0 flex-1">
            {notification.title && (
              <p className="text-sm font-medium text-gray-900">
                {notification.title}
                {retryCount > 0 && (
                  <span className="ml-2 text-xs text-gray-500">
                    (Attempt #{retryCount + 1})
                  </span>
                )}
              </p>
            )}
            <p
              className={`text-sm text-gray-500 ${notification.title ? 'mt-1' : ''}`}
            >
              {notification.message}
            </p>

            {/* Progress bar for operations */}
            {notification.showProgress && isRetrying && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>Processing...</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1">
                  <div
                    className="bg-blue-500 h-1 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Queue status */}
            {notification.showQueueStatus && retryQueue && (
              <div className="mt-2 text-xs text-gray-500">
                Queue: {retryQueue.pending} pending, {retryQueue.failed} failed
              </div>
            )}

            {/* Action buttons */}
            {(notification.actions || notification.retryAction) && (
              <div className="mt-3 flex space-x-2">
                {notification.retryAction && (
                  <button
                    onClick={handleRetry}
                    disabled={isRetrying}
                    className="text-sm font-medium text-blue-600 hover:text-blue-500 disabled:text-blue-300"
                  >
                    {isRetrying ? 'Retrying...' : 'Retry'}
                  </button>
                )}
                {notification.actions?.map((action, index) => (
                  <button
                    key={index}
                    onClick={action.onClick}
                    className={`text-sm font-medium ${action.style || 'text-gray-600 hover:text-gray-500'}`}
                  >
                    {action.label}
                  </button>
                ))}
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

// Queue status component
function QueueStatusIndicator({ retryQueue, onManageQueue }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const status = retryQueue.getQueueStatus()

  if (status.total === 0) return null

  return (
    <div className="fixed bottom-4 left-4 z-40">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-3">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            {status.retrying > 0 ? (
              <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />
            ) : status.failed > 0 ? (
              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
            ) : (
              <ClockIcon className="h-5 w-5 text-yellow-500" />
            )}
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900">Operation Queue</p>
            <p className="text-xs text-gray-500">
              {status.pending} pending, {status.failed} failed
            </p>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-400 hover:text-gray-500"
          >
            {isExpanded ? (
              <PauseIcon className="h-4 w-4" />
            ) : (
              <PlayIcon className="h-4 w-4" />
            )}
          </button>
        </div>

        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="flex space-x-2">
              <button
                onClick={() => retryQueue.retryFailedItems()}
                disabled={status.failed === 0}
                className="text-xs bg-blue-500 text-white px-2 py-1 rounded disabled:bg-gray-300"
              >
                Retry Failed
              </button>
              <button
                onClick={() => retryQueue.clearFailedItems()}
                disabled={status.failed === 0}
                className="text-xs bg-red-500 text-white px-2 py-1 rounded disabled:bg-gray-300"
              >
                Clear Failed
              </button>
              <button
                onClick={onManageQueue}
                className="text-xs bg-gray-500 text-white px-2 py-1 rounded"
              >
                Details
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Main enhanced toast system
export default function EnhancedToastSystem() {
  const [toasts, setToasts] = useState([])
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [offlineQueue, setOfflineQueue] = useState([])
  const retryQueue = useRef(new RetryQueueManager())
  const [queueStatus, setQueueStatus] = useState(
    retryQueue.current.getQueueStatus()
  )

  const { isAuthenticated } = useAuth()
  const { showError, showSuccess, showWarning } = useNotifications()

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Process offline queue when coming back online
      processOfflineQueue()

      showSuccess('Connection restored', 'Back Online', {
        duration: 3000,
        action: {
          label: 'Sync Data',
          onClick: () => processOfflineQueue(),
        },
      })
    }

    const handleOffline = () => {
      setIsOnline(false)
      showWarning(
        'Working offline. Changes will sync when connection is restored.',
        'Connection Lost'
      )
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [showSuccess, showWarning])

  // Process offline queue when connection is restored
  const processOfflineQueue = useCallback(async () => {
    if (offlineQueue.length === 0 || !isOnline) return

    const operations = [...offlineQueue]
    setOfflineQueue([])

    for (const operation of operations) {
      retryQueue.current.addToQueue({
        execute: operation.execute,
        onSuccess: (result) => {
          showSuccess(
            operation.successMessage || 'Operation completed',
            'Sync Complete'
          )
        },
        onFailure: (error, retryCount) => {
          showError(
            `${operation.errorMessage || 'Operation failed'} after ${retryCount} attempts`,
            'Sync Failed',
            {
              retryAction: () => retryQueue.current.addToQueue(operation),
            }
          )
        },
      })
    }

    setQueueStatus(retryQueue.current.getQueueStatus())
  }, [offlineQueue, isOnline, showSuccess, showError])

  // Update queue status periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setQueueStatus(retryQueue.current.getQueueStatus())
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // Enhanced toast creation with retry support
  const addEnhancedToast = useCallback(
    (notification) => {
      const id = Math.random().toString(36).substr(2, 9)
      const enhancedNotification = {
        id,
        type: notification.type || 'info',
        title: notification.title,
        message: notification.message,
        duration:
          notification.duration ||
          (notification.type === 'error' ? 8000 : 5000),
        persistent: notification.persistent || false,
        priority: notification.priority || 'normal',
        retryAction: notification.retryAction,
        autoCloseOnSuccess: notification.autoCloseOnSuccess !== false,
        showProgress: notification.showProgress || false,
        showQueueStatus: notification.showQueueStatus || false,
        actions: notification.actions,
        timestamp: Date.now(),
      }

      setToasts((prev) => {
        // Limit number of concurrent toasts
        const maxToasts = 5
        const filtered = prev.slice(-(maxToasts - 1))
        return [...filtered, enhancedNotification]
      })

      // Add to offline queue if offline and operation is provided
      if (!isOnline && notification.offlineOperation) {
        setOfflineQueue((prev) => [...prev, notification.offlineOperation])
      }

      return id
    },
    [isOnline]
  )

  // Remove toast
  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  // Handle retry attempts
  const handleRetry = useCallback((toastId, error) => {
    // Could add more sophisticated retry logic here
    console.log('Retry failed for toast:', toastId, error)
  }, [])

  // Listen for enhanced notification events
  useEffect(() => {
    const handleEnhancedNotification = (event) => {
      addEnhancedToast(event.detail)
    }

    window.addEventListener(
      'createEnhancedNotification',
      handleEnhancedNotification
    )
    return () => {
      window.removeEventListener(
        'createEnhancedNotification',
        handleEnhancedNotification
      )
    }
  }, [addEnhancedToast])

  const handleManageQueue = useCallback(() => {
    // Could open a detailed queue management modal
    console.log('Queue details:', retryQueue.current.queue)
  }, [])

  return (
    <>
      {/* Enhanced toast notifications container */}
      {toasts.length > 0 &&
        createPortal(
          <div className="fixed inset-0 z-50 flex flex-col items-end justify-start p-6 space-y-4 pointer-events-none">
            {toasts.map((toast) => (
              <EnhancedToast
                key={toast.id}
                notification={toast}
                onClose={removeToast}
                onRetry={handleRetry}
                retryQueue={queueStatus}
              />
            ))}
          </div>,
          document.body
        )}

      {/* Queue status indicator */}
      <QueueStatusIndicator
        retryQueue={retryQueue.current}
        onManageQueue={handleManageQueue}
      />

      {/* Offline indicator */}
      {!isOnline &&
        createPortal(
          <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-60">
            <div className="bg-yellow-100 border border-yellow-300 rounded-lg px-4 py-2 shadow-lg">
              <div className="flex items-center space-x-2">
                <WifiIcon className="h-5 w-5 text-yellow-600" />
                <span className="text-sm font-medium text-yellow-800">
                  Working Offline
                </span>
                <span className="text-xs text-yellow-600">
                  {offlineQueue.length > 0 &&
                    `${offlineQueue.length} changes queued`}
                </span>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  )
}

// Enhanced notification creation utilities
export const createEnhancedNotification = (notification) => {
  const event = new CustomEvent('createEnhancedNotification', {
    detail: notification,
  })
  window.dispatchEvent(event)
}

export const createRetryableNotification = (notification, retryFn) => {
  createEnhancedNotification({
    ...notification,
    retryAction: retryFn,
    showProgress: true,
    autoCloseOnSuccess: true,
  })
}

export const createOfflineCapableNotification = (
  notification,
  offlineOperation
) => {
  createEnhancedNotification({
    ...notification,
    offlineOperation,
    showQueueStatus: true,
  })
}
