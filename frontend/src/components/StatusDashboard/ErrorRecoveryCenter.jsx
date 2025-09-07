import { useState, useEffect, useCallback } from 'react'
import {
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  InformationCircleIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  BugAntIcon,
  WrenchScrewdriverIcon,
  ChartBarIcon,
  PlayIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import { useEnhancedRetry } from '../../hooks/useEnhancedRetry'
import { useNotifications } from '../../hooks/useNotifications'
import { useEnhancedApi } from '../../hooks/useEnhancedApi'

// Error classification and recovery strategies
const ERROR_CATEGORIES = {
  network: {
    name: 'Network Issues',
    icon: CpuChipIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    strategies: [
      'connection_retry',
      'endpoint_fallback',
      'offline_mode',
      'cache_fallback',
    ],
    autoRecovery: true,
    priority: 'high',
  },
  authentication: {
    name: 'Authentication',
    icon: ShieldCheckIcon,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    strategies: ['token_refresh', 'relogin_prompt', 'oauth_reconnect'],
    autoRecovery: false,
    priority: 'critical',
  },
  server_error: {
    name: 'Server Errors',
    icon: ExclamationTriangleIcon,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    strategies: [
      'service_restart',
      'load_balancer_switch',
      'graceful_degradation',
    ],
    autoRecovery: true,
    priority: 'high',
  },
  data_corruption: {
    name: 'Data Issues',
    icon: BugAntIcon,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    strategies: [
      'data_validation',
      'backup_restore',
      'cache_clear',
      'state_reset',
    ],
    autoRecovery: false,
    priority: 'critical',
  },
  rate_limiting: {
    name: 'Rate Limiting',
    icon: ClockIcon,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    strategies: ['backoff_retry', 'queue_requests', 'load_distribution'],
    autoRecovery: true,
    priority: 'medium',
  },
  performance: {
    name: 'Performance',
    icon: ChartBarIcon,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    strategies: [
      'resource_optimization',
      'cache_warming',
      'query_optimization',
      'memory_cleanup',
    ],
    autoRecovery: true,
    priority: 'medium',
  },
}

const RECOVERY_STRATEGIES = {
  connection_retry: {
    name: 'Connection Retry',
    description: 'Retry failed network connections with exponential backoff',
    automated: true,
    estimatedTime: 30,
    successRate: 85,
  },
  token_refresh: {
    name: 'Token Refresh',
    description: 'Refresh expired authentication tokens',
    automated: true,
    estimatedTime: 5,
    successRate: 95,
  },
  service_restart: {
    name: 'Service Restart',
    description: 'Restart affected services or components',
    automated: false,
    estimatedTime: 120,
    successRate: 90,
  },
  cache_clear: {
    name: 'Cache Clear',
    description: 'Clear corrupted cache data',
    automated: true,
    estimatedTime: 10,
    successRate: 80,
  },
  offline_mode: {
    name: 'Offline Mode',
    description: 'Enable offline functionality with local storage',
    automated: true,
    estimatedTime: 5,
    successRate: 70,
  },
  graceful_degradation: {
    name: 'Graceful Degradation',
    description: 'Disable non-critical features to maintain core functionality',
    automated: true,
    estimatedTime: 15,
    successRate: 85,
  },
  relogin_prompt: {
    name: 'Re-login Prompt',
    description: 'Prompt user to re-authenticate',
    automated: false,
    estimatedTime: 60,
    successRate: 98,
  },
  backup_restore: {
    name: 'Backup Restore',
    description: 'Restore data from last known good backup',
    automated: false,
    estimatedTime: 300,
    successRate: 95,
  },
}

// Individual error incident component
function ErrorIncident({ error, onRecover, onDismiss, onDetails }) {
  const [isRecovering, setIsRecovering] = useState(false)
  const [recoveryProgress, setRecoveryProgress] = useState(0)
  const [selectedStrategy, setSelectedStrategy] = useState(null)

  const category = ERROR_CATEGORIES[error.category] || ERROR_CATEGORIES.network
  const strategies = category.strategies.map((id) => ({
    id,
    ...RECOVERY_STRATEGIES[id],
  }))

  const handleRecover = async (strategyId) => {
    setIsRecovering(true)
    setSelectedStrategy(strategyId)
    setRecoveryProgress(0)

    const strategy = RECOVERY_STRATEGIES[strategyId]

    try {
      // Simulate recovery progress
      const progressInterval = setInterval(() => {
        setRecoveryProgress((prev) => {
          if (prev >= 90) return 90
          return prev + Math.random() * 10
        })
      }, strategy.estimatedTime * 10)

      await onRecover(error.id, strategyId)

      clearInterval(progressInterval)
      setRecoveryProgress(100)

      setTimeout(() => {
        setIsRecovering(false)
        setRecoveryProgress(0)
        setSelectedStrategy(null)
      }, 1000)
    } catch (recoveryError) {
      setIsRecovering(false)
      setRecoveryProgress(0)
      setSelectedStrategy(null)
      throw recoveryError
    }
  }

  return (
    <div
      className={`border-l-4 ${category.borderColor} bg-white rounded-r-lg shadow-sm p-4 mb-4`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className={`p-2 rounded-full ${category.bgColor} flex-shrink-0`}>
            <category.icon className={`h-5 w-5 ${category.color}`} />
          </div>

          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <h3 className="font-semibold text-gray-900">{error.title}</h3>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                  error.severity === 'critical'
                    ? 'bg-red-100 text-red-800'
                    : error.severity === 'high'
                      ? 'bg-orange-100 text-orange-800'
                      : error.severity === 'medium'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                }`}
              >
                {error.severity}
              </span>
              {category.autoRecovery && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                  Auto-recovery
                </span>
              )}
            </div>

            <p className="text-gray-600 text-sm mb-3">{error.message}</p>

            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <span>Occurred: {error.timestamp.toLocaleTimeString()}</span>
              <span>Category: {category.name}</span>
              <span>
                Affected: {error.affectedComponents?.join(', ') || 'Unknown'}
              </span>
            </div>

            {/* Recovery Progress */}
            {isRecovering && (
              <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-blue-900">
                    Executing: {RECOVERY_STRATEGIES[selectedStrategy]?.name}
                  </span>
                  <span className="text-sm text-blue-600">
                    {Math.round(recoveryProgress)}%
                  </span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${recoveryProgress}%` }}
                  />
                </div>
                <p className="text-xs text-blue-600 mt-1">
                  {RECOVERY_STRATEGIES[selectedStrategy]?.description}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          <button
            onClick={() => onDetails(error)}
            className="p-2 text-gray-400 hover:text-gray-600 rounded"
            title="View Details"
          >
            <InformationCircleIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDismiss(error.id)}
            className="p-2 text-gray-400 hover:text-gray-600 rounded"
            title="Dismiss"
          >
            <XCircleIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Recovery Actions */}
      {!isRecovering && (
        <div className="mt-4 flex flex-wrap gap-2">
          {strategies.slice(0, 3).map((strategy) => (
            <button
              key={strategy.id}
              onClick={() => handleRecover(strategy.id)}
              className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                strategy.automated
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {strategy.automated ? (
                <PlayIcon className="h-3 w-3 mr-1" />
              ) : (
                <WrenchScrewdriverIcon className="h-3 w-3 mr-1" />
              )}
              {strategy.name}
              <span className="ml-1 text-xs opacity-75">
                (~{strategy.estimatedTime}s)
              </span>
            </button>
          ))}

          {strategies.length > 3 && (
            <button
              onClick={() => onDetails(error)}
              className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
            >
              +{strategies.length - 3} more
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Recovery center dashboard
export default function ErrorRecoveryCenter() {
  const [errors, setErrors] = useState([])
  const [autoRecoveryEnabled, setAutoRecoveryEnabled] = useState(true)
  const [selectedError, setSelectedError] = useState(null)
  const [recoveryHistory, setRecoveryHistory] = useState([])
  const [isMonitoring, setIsMonitoring] = useState(true)

  const { executeWithRetry, getAllOperations } = useEnhancedRetry()
  const { showSuccess, showWarning } = useNotifications()
  const { connectionStatus } = useEnhancedApi()

  // Simulate error detection and reporting (replace with real error monitoring)
  useEffect(() => {
    if (!isMonitoring) return

    const detectErrors = () => {
      // Check failed operations from retry system
      const failedOps = getAllOperations().filter(
        (op) => op.status === 'failed'
      )

      failedOps.forEach((op) => {
        const existingError = errors.find((e) => e.operationId === op.id)
        if (!existingError) {
          const error = {
            id: Math.random().toString(36).substr(2, 9),
            operationId: op.id,
            title: `Operation Failed: ${op.strategy}`,
            message: op.error || 'Unknown error occurred',
            category: classifyError(op.error),
            severity: op.attempts >= 3 ? 'high' : 'medium',
            timestamp: new Date(),
            affectedComponents: ['API', 'Client'],
            context: op,
          }

          setErrors((prev) => [...prev, error])

          if (
            autoRecoveryEnabled &&
            ERROR_CATEGORIES[error.category]?.autoRecovery
          ) {
            setTimeout(() => autoRecover(error), 2000)
          }
        }
      })

      // Check connection status
      if (connectionStatus === 'disconnected') {
        const existingError = errors.find(
          (e) => e.category === 'network' && e.title.includes('Connection')
        )
        if (!existingError) {
          const error = {
            id: Math.random().toString(36).substr(2, 9),
            title: 'Connection Lost',
            message: 'Unable to connect to the server',
            category: 'network',
            severity: 'high',
            timestamp: new Date(),
            affectedComponents: ['API', 'WebSocket'],
          }

          setErrors((prev) => [...prev, error])

          if (autoRecoveryEnabled) {
            setTimeout(() => autoRecover(error), 3000)
          }
        }
      }
    }

    const interval = setInterval(detectErrors, 10000)
    return () => clearInterval(interval)
  }, [
    errors,
    autoRecoveryEnabled,
    isMonitoring,
    getAllOperations,
    connectionStatus,
    autoRecover,
  ])

  // Auto-recovery logic
  const autoRecover = useCallback(
    async (error) => {
      const category = ERROR_CATEGORIES[error.category]
      if (!category?.autoRecovery) return

      const automaticStrategies = category.strategies.filter(
        (id) => RECOVERY_STRATEGIES[id].automated
      )

      if (automaticStrategies.length > 0) {
        const bestStrategy = automaticStrategies[0] // Use first/best strategy

        try {
          await handleRecover(error.id, bestStrategy)
          showSuccess(
            `Auto-recovery successful for ${error.title}`,
            'Recovery Complete'
          )
        } catch (recoveryError) {
          showWarning(
            `Auto-recovery failed for ${error.title}`,
            'Recovery Failed'
          )
        }
      }
    },
    [showSuccess, showWarning, handleRecover]
  )

  // Classify errors based on message content
  const classifyError = (errorMessage) => {
    if (!errorMessage) return 'network'

    const message = errorMessage.toLowerCase()

    if (
      message.includes('network') ||
      message.includes('fetch') ||
      message.includes('timeout')
    ) {
      return 'network'
    } else if (
      message.includes('auth') ||
      message.includes('token') ||
      message.includes('unauthorized')
    ) {
      return 'authentication'
    } else if (
      message.includes('500') ||
      message.includes('502') ||
      message.includes('503')
    ) {
      return 'server_error'
    } else if (message.includes('429') || message.includes('rate limit')) {
      return 'rate_limiting'
    } else if (
      message.includes('data') ||
      message.includes('validation') ||
      message.includes('corrupt')
    ) {
      return 'data_corruption'
    } else if (
      message.includes('slow') ||
      message.includes('performance') ||
      message.includes('memory')
    ) {
      return 'performance'
    }

    return 'network'
  }

  // Handle manual recovery
  const handleRecover = useCallback(
    async (errorId, strategyId) => {
      const error = errors.find((e) => e.id === errorId)
      if (!error) return

      const strategy = RECOVERY_STRATEGIES[strategyId]

      // Record recovery attempt (declared outside try/catch for proper scope)
      const recoveryAttempt = {
        id: Math.random().toString(36).substr(2, 9),
        errorId,
        strategyId,
        strategyName: strategy.name,
        timestamp: new Date(),
        status: 'in_progress',
      }

      try {
        setRecoveryHistory((prev) => [recoveryAttempt, ...prev])

        // Execute recovery based on strategy
        switch (strategyId) {
          case 'connection_retry':
            await executeWithRetry(() => fetch('/api/health'), {
              strategy: 'aggressive',
              maxRetries: 3,
            })
            break

          case 'token_refresh':
            // Trigger token refresh
            window.dispatchEvent(new CustomEvent('refreshToken'))
            break

          case 'cache_clear':
            // Clear local caches
            localStorage.clear()
            sessionStorage.clear()
            if ('caches' in window) {
              const cacheNames = await caches.keys()
              await Promise.all(cacheNames.map((name) => caches.delete(name)))
            }
            break

          case 'offline_mode':
            // Enable offline functionality
            window.dispatchEvent(new CustomEvent('enableOfflineMode'))
            break

          case 'graceful_degradation':
            // Disable non-critical features
            window.dispatchEvent(new CustomEvent('enableDegradedMode'))
            break

          default:
            throw new Error(`Recovery strategy ${strategyId} not implemented`)
        }

        // Update recovery status
        setRecoveryHistory((prev) =>
          prev.map((r) =>
            r.id === recoveryAttempt.id
              ? { ...r, status: 'completed', completedAt: new Date() }
              : r
          )
        )

        // Remove the error if recovery was successful
        setErrors((prev) => prev.filter((e) => e.id !== errorId))
      } catch (recoveryError) {
        // Update recovery status as failed
        setRecoveryHistory((prev) =>
          prev.map((r) =>
            r.id === recoveryAttempt.id
              ? {
                  ...r,
                  status: 'failed',
                  error: recoveryError.message,
                  completedAt: new Date(),
                }
              : r
          )
        )

        throw recoveryError
      }
    },
    [errors, executeWithRetry]
  )

  const handleDismiss = useCallback((errorId) => {
    setErrors((prev) => prev.filter((e) => e.id !== errorId))
  }, [])

  const handleDetails = useCallback((error) => {
    setSelectedError(error)
  }, [])

  const getErrorStats = () => {
    const critical = errors.filter((e) => e.severity === 'critical').length
    const high = errors.filter((e) => e.severity === 'high').length
    const medium = errors.filter((e) => e.severity === 'medium').length

    return { critical, high, medium, total: errors.length }
  }

  const stats = getErrorStats()

  return (
    <div className="space-y-6">
      {/* Control Panel */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Error Recovery Center
            </h2>
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isMonitoring ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                }`}
              />
              <span className="text-sm text-gray-600">
                {isMonitoring ? 'Monitoring Active' : 'Monitoring Paused'}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRecoveryEnabled}
                onChange={(e) => setAutoRecoveryEnabled(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded"
              />
              <span className="text-sm text-gray-700">Auto Recovery</span>
            </label>

            <button
              onClick={() => setIsMonitoring(!isMonitoring)}
              className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium ${
                isMonitoring
                  ? 'bg-red-100 text-red-700 hover:bg-red-200'
                  : 'bg-green-100 text-green-700 hover:bg-green-200'
              }`}
            >
              {isMonitoring ? (
                <>
                  <PauseIcon className="h-4 w-4 mr-1" />
                  Pause Monitoring
                </>
              ) : (
                <>
                  <PlayIcon className="h-4 w-4 mr-1" />
                  Resume Monitoring
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Errors</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <ExclamationTriangleIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Critical</p>
              <p className="text-2xl font-bold text-red-600">
                {stats.critical}
              </p>
            </div>
            <XCircleIcon className="h-8 w-8 text-red-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">High Priority</p>
              <p className="text-2xl font-bold text-orange-600">{stats.high}</p>
            </div>
            <ExclamationTriangleIcon className="h-8 w-8 text-orange-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Auto-Recovered</p>
              <p className="text-2xl font-bold text-green-600">
                {recoveryHistory.filter((r) => r.status === 'completed').length}
              </p>
            </div>
            <CheckCircleIcon className="h-8 w-8 text-green-400" />
          </div>
        </div>
      </div>

      {/* Active Errors */}
      {errors.length > 0 ? (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Active Errors ({errors.length})
          </h3>
          {errors.map((error) => (
            <ErrorIncident
              key={error.id}
              error={error}
              onRecover={handleRecover}
              onDismiss={handleDismiss}
              onDetails={handleDetails}
            />
          ))}
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
          <CheckCircleIcon className="h-12 w-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-green-900 mb-2">
            All Systems Healthy
          </h3>
          <p className="text-green-700">
            No errors detected. The system is running smoothly.
          </p>
        </div>
      )}

      {/* Recovery History */}
      {recoveryHistory.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Recovery History
          </h3>
          <div className="space-y-3">
            {recoveryHistory.slice(0, 5).map((recovery) => (
              <div
                key={recovery.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {recovery.status === 'completed' ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : recovery.status === 'failed' ? (
                    <XCircleIcon className="h-5 w-5 text-red-500" />
                  ) : (
                    <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />
                  )}

                  <div>
                    <p className="font-medium text-gray-900">
                      {recovery.strategyName}
                    </p>
                    <p className="text-sm text-gray-600">
                      {recovery.timestamp.toLocaleString()}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      recovery.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : recovery.status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {recovery.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Details Modal */}
      {selectedError && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Error Details
                </h3>
                <button
                  onClick={() => setSelectedError(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">
                    Error Information
                  </h4>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    <p>
                      <span className="font-medium">Title:</span>{' '}
                      {selectedError.title}
                    </p>
                    <p>
                      <span className="font-medium">Message:</span>{' '}
                      {selectedError.message}
                    </p>
                    <p>
                      <span className="font-medium">Category:</span>{' '}
                      {ERROR_CATEGORIES[selectedError.category]?.name}
                    </p>
                    <p>
                      <span className="font-medium">Severity:</span>{' '}
                      {selectedError.severity}
                    </p>
                    <p>
                      <span className="font-medium">Timestamp:</span>{' '}
                      {selectedError.timestamp.toLocaleString()}
                    </p>
                  </div>
                </div>

                {selectedError.context && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Context</h4>
                    <pre className="bg-gray-50 rounded-lg p-4 text-xs overflow-x-auto">
                      {JSON.stringify(selectedError.context, null, 2)}
                    </pre>
                  </div>
                )}

                <div>
                  <h4 className="font-medium text-gray-900 mb-2">
                    Available Recovery Strategies
                  </h4>
                  <div className="space-y-2">
                    {ERROR_CATEGORIES[selectedError.category]?.strategies.map(
                      (strategyId) => {
                        const strategy = RECOVERY_STRATEGIES[strategyId]
                        return (
                          <div
                            key={strategyId}
                            className="flex items-center justify-between p-3 border rounded-lg"
                          >
                            <div>
                              <p className="font-medium text-gray-900">
                                {strategy.name}
                              </p>
                              <p className="text-sm text-gray-600">
                                {strategy.description}
                              </p>
                              <p className="text-xs text-gray-500">
                                Success rate: {strategy.successRate}% • Est.
                                time: {strategy.estimatedTime}s
                              </p>
                            </div>
                            <button
                              onClick={() => {
                                setSelectedError(null)
                                handleRecover(selectedError.id, strategyId)
                              }}
                              className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                            >
                              Execute
                            </button>
                          </div>
                        )
                      }
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
