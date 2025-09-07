import { useState, useCallback, useRef, useEffect } from 'react'
import { useNotifications } from './useNotifications'

// Enhanced retry strategies
const RETRY_STRATEGIES = {
  immediate: {
    delays: [100, 500, 1000],
    maxRetries: 3,
    backoffMultiplier: 1,
  },
  gradual: {
    delays: [1000, 2000, 5000],
    maxRetries: 3,
    backoffMultiplier: 2,
  },
  patient: {
    delays: [2000, 5000, 15000],
    maxRetries: 3,
    backoffMultiplier: 2.5,
  },
  aggressive: {
    delays: [500, 1000, 2000, 5000, 10000],
    maxRetries: 5,
    backoffMultiplier: 2,
  },
  custom: {
    delays: [],
    maxRetries: 0,
    backoffMultiplier: 1,
  },
}

// Error classification for smart retry logic
const ERROR_CATEGORIES = {
  network: {
    patterns: [
      'NetworkError',
      'Failed to fetch',
      'ERR_NETWORK',
      'ERR_INTERNET_DISCONNECTED',
    ],
    shouldRetry: true,
    strategy: 'gradual',
  },
  server: {
    patterns: ['500', '502', '503', '504'],
    shouldRetry: true,
    strategy: 'patient',
  },
  rate_limit: {
    patterns: ['429', 'rate limit', 'too many requests'],
    shouldRetry: true,
    strategy: 'patient',
  },
  authentication: {
    patterns: ['401', '403', 'Unauthorized', 'Forbidden'],
    shouldRetry: false,
    strategy: null,
  },
  validation: {
    patterns: ['400', 'Bad Request', 'validation'],
    shouldRetry: false,
    strategy: null,
  },
  not_found: {
    patterns: ['404', 'Not Found'],
    shouldRetry: false,
    strategy: null,
  },
}

// Classify error to determine retry strategy
function classifyError(error) {
  const errorMessage = error?.message || error?.toString() || ''
  const errorStatus = error?.status || error?.response?.status || 0

  for (const [category, config] of Object.entries(ERROR_CATEGORIES)) {
    const matchesPattern = config.patterns.some(
      (pattern) =>
        errorMessage.toLowerCase().includes(pattern.toLowerCase()) ||
        errorStatus.toString().includes(pattern)
    )

    if (matchesPattern) {
      return {
        category,
        shouldRetry: config.shouldRetry,
        recommendedStrategy: config.strategy,
      }
    }
  }

  // Default classification
  return {
    category: 'unknown',
    shouldRetry: true,
    recommendedStrategy: 'gradual',
  }
}

// Individual retry operation manager
class RetryOperation {
  constructor(id, operation, options = {}) {
    this.id = id
    this.operation = operation
    this.options = {
      strategy: 'gradual',
      maxRetries: 3,
      customDelays: null,
      onProgress: null,
      onSuccess: null,
      onError: null,
      onFinalFailure: null,
      context: {},
      ...options,
    }

    this.attempts = 0
    this.status = 'pending' // pending, running, completed, failed
    this.lastError = null
    this.startTime = null
    this.endTime = null
    this.isAborted = false
    this.abortController = new AbortController()
  }

  async execute() {
    if (this.isAborted) {
      throw new Error('Operation aborted')
    }

    this.status = 'running'
    this.startTime = Date.now()
    this.attempts++

    try {
      const result = await this.operation(this.abortController.signal, {
        attempt: this.attempts,
        context: this.options.context,
      })

      this.status = 'completed'
      this.endTime = Date.now()

      if (this.options.onSuccess) {
        this.options.onSuccess(result, this.attempts)
      }

      return result
    } catch (error) {
      this.lastError = error

      if (this.options.onError) {
        this.options.onError(error, this.attempts)
      }

      throw error
    }
  }

  abort() {
    this.isAborted = true
    this.abortController.abort()
    this.status = 'failed'
    this.endTime = Date.now()
  }

  canRetry() {
    if (this.isAborted) return false

    const strategy =
      RETRY_STRATEGIES[this.options.strategy] || RETRY_STRATEGIES.gradual
    const maxRetries = this.options.maxRetries || strategy.maxRetries

    if (this.attempts >= maxRetries) return false

    // Check if error is retryable
    if (this.lastError) {
      const classification = classifyError(this.lastError)
      return classification.shouldRetry
    }

    return true
  }

  getNextDelay() {
    const strategy =
      RETRY_STRATEGIES[this.options.strategy] || RETRY_STRATEGIES.gradual

    if (this.options.customDelays) {
      return this.options.customDelays[
        Math.min(this.attempts, this.options.customDelays.length - 1)
      ]
    }

    const baseDelay =
      strategy.delays[Math.min(this.attempts - 1, strategy.delays.length - 1)]
    return (
      baseDelay *
      Math.pow(
        strategy.backoffMultiplier,
        Math.max(0, this.attempts - strategy.delays.length)
      )
    )
  }

  getDuration() {
    const end = this.endTime || Date.now()
    return this.startTime ? end - this.startTime : 0
  }

  getProgress() {
    const strategy =
      RETRY_STRATEGIES[this.options.strategy] || RETRY_STRATEGIES.gradual
    const maxRetries = this.options.maxRetries || strategy.maxRetries
    return Math.min(this.attempts / maxRetries, 1) * 100
  }
}

// Enhanced retry hook
export function useEnhancedRetry() {
  const [operations, setOperations] = useState(new Map())
  const [globalStats, setGlobalStats] = useState({
    total: 0,
    successful: 0,
    failed: 0,
    pending: 0,
  })
  const [preferences, setPreferences] = useState({
    strategy: 'gradual',
    maxConcurrent: 3,
    enableNotifications: true,
    enableSmartRetry: true,
  })

  const { showError, showSuccess, showWarning, showInfo, notifyApiError } =
    useNotifications()
  const timeouts = useRef(new Map())
  const operationQueue = useRef([])

  // Load preferences from localStorage
  useEffect(() => {
    const loadPreferences = () => {
      try {
        const stored = localStorage.getItem('retryPreferences')
        if (stored) {
          setPreferences((prev) => ({ ...prev, ...JSON.parse(stored) }))
        }
      } catch (error) {
        console.error('Failed to load retry preferences:', error)
      }
    }

    loadPreferences()

    // Listen for preference changes
    const handlePreferencesChange = (event) => {
      if (event.detail?.retryStrategy) {
        setPreferences((prev) => ({
          ...prev,
          strategy: event.detail.retryStrategy,
        }))
      }
    }

    window.addEventListener(
      'notificationPreferencesChanged',
      handlePreferencesChange
    )
    return () =>
      window.removeEventListener(
        'notificationPreferencesChanged',
        handlePreferencesChange
      )
  }, [])

  // Update global stats
  useEffect(() => {
    const updateStats = () => {
      const ops = Array.from(operations.values())
      setGlobalStats({
        total: ops.length,
        successful: ops.filter((op) => op.status === 'completed').length,
        failed: ops.filter((op) => op.status === 'failed').length,
        pending: ops.filter(
          (op) => op.status === 'pending' || op.status === 'running'
        ).length,
      })
    }

    updateStats()
  }, [operations])

  // Process operation queue
  const processQueue = useCallback(async () => {
    const runningOps = Array.from(operations.values()).filter(
      (op) => op.status === 'running'
    )
    if (runningOps.length >= preferences.maxConcurrent) {
      return // Wait for some operations to complete
    }

    const nextOperation = operationQueue.current.shift()
    if (!nextOperation) return

    const delay = nextOperation.getNextDelay()

    const timeoutId = setTimeout(async () => {
      timeouts.current.delete(nextOperation.id)

      try {
        const result = await nextOperation.execute()

        if (preferences.enableNotifications) {
          showSuccess(
            `Operation completed after ${nextOperation.attempts} attempts`,
            'Retry Successful'
          )
        }

        // Remove completed operation after delay
        setTimeout(() => {
          setOperations((prev) => {
            const newOps = new Map(prev)
            newOps.delete(nextOperation.id)
            return newOps
          })
        }, 5000)
      } catch (error) {
        if (nextOperation.canRetry()) {
          // Add back to queue for retry
          operationQueue.current.push(nextOperation)

          if (preferences.enableNotifications) {
            showWarning(
              `Attempt ${nextOperation.attempts} failed. Retrying in ${Math.round(nextOperation.getNextDelay() / 1000)}s...`,
              'Retry Scheduled',
              { duration: 3000 }
            )
          }

          // Process next in queue
          setTimeout(processQueue, 100)
        } else {
          nextOperation.status = 'failed'

          if (nextOperation.options.onFinalFailure) {
            nextOperation.options.onFinalFailure(error, nextOperation.attempts)
          }

          if (preferences.enableNotifications) {
            showError(
              `Operation failed after ${nextOperation.attempts} attempts`,
              'Retry Failed',
              {
                duration: 10000,
                action: {
                  label: 'Retry Manually',
                  onClick: () => retryOperation(nextOperation.id),
                },
              }
            )
          }
        }
      }

      // Update operations map
      setOperations((prev) => new Map(prev))

      // Continue processing queue
      setTimeout(processQueue, 100)
    }, delay)

    timeouts.current.set(nextOperation.id, timeoutId)
  }, [operations, preferences, showSuccess, showError, showWarning])

  // Create and execute a retryable operation
  const executeWithRetry = useCallback(
    async (operation, options = {}) => {
      const id = Math.random().toString(36).substr(2, 9)

      // Smart retry - adjust strategy based on error classification
      let finalOptions = { ...options }
      if (preferences.enableSmartRetry && options.lastError) {
        const classification = classifyError(options.lastError)
        if (classification.recommendedStrategy) {
          finalOptions.strategy = classification.recommendedStrategy
        }
      }

      // Use global preferences as defaults
      finalOptions = {
        strategy: preferences.strategy,
        ...finalOptions,
      }

      const retryOp = new RetryOperation(id, operation, finalOptions)

      setOperations((prev) => new Map(prev.set(id, retryOp)))

      // Try immediate execution first
      try {
        const result = await retryOp.execute()

        if (preferences.enableNotifications) {
          showSuccess('Operation completed successfully', 'Success')
        }

        // Remove completed operation after delay
        setTimeout(() => {
          setOperations((prev) => {
            const newOps = new Map(prev)
            newOps.delete(id)
            return newOps
          })
        }, 3000)

        return result
      } catch (error) {
        if (retryOp.canRetry()) {
          // Add to retry queue
          operationQueue.current.push(retryOp)
          processQueue()

          if (preferences.enableNotifications) {
            const classification = classifyError(error)
            showInfo(
              `Operation failed (${classification.category}). Retrying automatically...`,
              'Scheduling Retry',
              { duration: 4000 }
            )
          }

          // Return a promise that resolves when retry completes or fails
          return new Promise((resolve, reject) => {
            retryOp.options.onSuccess = (result) => resolve(result)
            retryOp.options.onFinalFailure = (error) => reject(error)
          })
        } else {
          retryOp.status = 'failed'

          if (preferences.enableNotifications) {
            notifyApiError(`Operation failed: ${error.message}`, () =>
              retryOperation(id)
            )
          }

          throw error
        }
      }
    },
    [
      preferences,
      showSuccess,
      showError,
      showInfo,
      notifyApiError,
      processQueue,
    ]
  )

  // Manually retry a specific operation
  const retryOperation = useCallback(
    async (operationId) => {
      const operation = operations.get(operationId)
      if (!operation) return

      // Reset operation state
      operation.attempts = 0
      operation.status = 'pending'
      operation.lastError = null
      operation.isAborted = false
      operation.abortController = new AbortController()

      // Add to queue
      operationQueue.current.push(operation)
      processQueue()
    },
    [operations, processQueue]
  )

  // Abort a specific operation
  const abortOperation = useCallback(
    (operationId) => {
      const operation = operations.get(operationId)
      if (operation) {
        operation.abort()

        // Clear timeout if exists
        const timeoutId = timeouts.current.get(operationId)
        if (timeoutId) {
          clearTimeout(timeoutId)
          timeouts.current.delete(operationId)
        }

        // Remove from queue
        operationQueue.current = operationQueue.current.filter(
          (op) => op.id !== operationId
        )

        setOperations((prev) => new Map(prev))
      }
    },
    [operations]
  )

  // Abort all operations
  const abortAllOperations = useCallback(() => {
    operations.forEach((operation) => {
      operation.abort()
    })

    timeouts.current.forEach((timeoutId) => {
      clearTimeout(timeoutId)
    })
    timeouts.current.clear()

    operationQueue.current = []
    setOperations(new Map())
  }, [operations])

  // Clear completed/failed operations
  const clearCompleted = useCallback(() => {
    setOperations((prev) => {
      const newOps = new Map()
      prev.forEach((op, id) => {
        if (op.status === 'pending' || op.status === 'running') {
          newOps.set(id, op)
        }
      })
      return newOps
    })
  }, [])

  // Update preferences
  const updatePreferences = useCallback(
    (newPreferences) => {
      const updated = { ...preferences, ...newPreferences }
      setPreferences(updated)

      try {
        localStorage.setItem('retryPreferences', JSON.stringify(updated))
      } catch (error) {
        console.error('Failed to save retry preferences:', error)
      }
    },
    [preferences]
  )

  // Get operation status
  const getOperationStatus = useCallback(
    (operationId) => {
      return operations.get(operationId)
    },
    [operations]
  )

  // Get all operations as array
  const getAllOperations = useCallback(() => {
    return Array.from(operations.values()).map((op) => ({
      id: op.id,
      status: op.status,
      attempts: op.attempts,
      duration: op.getDuration(),
      progress: op.getProgress(),
      error: op.lastError?.message,
      canRetry: op.canRetry(),
      strategy: op.options.strategy,
    }))
  }, [operations])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      timeouts.current.forEach((timeoutId) => clearTimeout(timeoutId))
      timeouts.current.clear()
    }
  }, [])

  return {
    executeWithRetry,
    retryOperation,
    abortOperation,
    abortAllOperations,
    clearCompleted,
    getOperationStatus,
    getAllOperations,
    globalStats,
    preferences,
    updatePreferences,

    // Utility functions
    classifyError,
    RETRY_STRATEGIES,
    ERROR_CATEGORIES,
  }
}

export default useEnhancedRetry
