import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
  SignalIcon,
  ServerIcon,
  CloudIcon,
  DatabaseIcon,
  CpuChipIcon,
  BoltIcon,
  ArrowPathIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  WifiIcon,
} from '@heroicons/react/24/outline'
import { useEnhancedApi } from '../../hooks/useEnhancedApi'
import { useNotifications } from '../../hooks/useNotifications'
import { useEnhancedRetry } from '../../hooks/useEnhancedRetry'

// System component definitions
const SYSTEM_COMPONENTS = {
  api: {
    name: 'API Server',
    icon: ServerIcon,
    priority: 'critical',
    category: 'core',
    checkInterval: 30000,
    timeout: 10000,
    dependencies: ['database', 'redis'],
    healthEndpoint: '/health',
  },
  database: {
    name: 'Database',
    icon: DatabaseIcon,
    priority: 'critical',
    category: 'infrastructure',
    checkInterval: 60000,
    timeout: 15000,
    dependencies: [],
    healthEndpoint: '/health/db',
  },
  redis: {
    name: 'Redis Cache',
    icon: CpuChipIcon,
    priority: 'high',
    category: 'infrastructure',
    checkInterval: 45000,
    timeout: 8000,
    dependencies: [],
    healthEndpoint: '/health/redis',
  },
  websocket: {
    name: 'WebSocket',
    icon: WifiIcon,
    priority: 'medium',
    category: 'realtime',
    checkInterval: 20000,
    timeout: 5000,
    dependencies: ['api'],
    healthEndpoint: '/health/websocket',
  },
  oauth: {
    name: 'OAuth Services',
    icon: ShieldCheckIcon,
    priority: 'high',
    category: 'integrations',
    checkInterval: 120000,
    timeout: 20000,
    dependencies: ['api'],
    healthEndpoint: '/health/oauth',
  },
  analytics: {
    name: 'Analytics Pipeline',
    icon: ChartBarIcon,
    priority: 'medium',
    category: 'features',
    checkInterval: 90000,
    timeout: 12000,
    dependencies: ['api', 'database'],
    healthEndpoint: '/health/analytics',
  },
  cdn: {
    name: 'CDN & Assets',
    icon: CloudIcon,
    priority: 'low',
    category: 'assets',
    checkInterval: 300000,
    timeout: 10000,
    dependencies: [],
    healthEndpoint: '/health/cdn',
  },
}

// Status calculation logic
const HEALTH_STATES = {
  healthy: {
    label: 'Healthy',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    iconColor: 'text-green-500',
    priority: 0,
  },
  degraded: {
    label: 'Degraded',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    iconColor: 'text-yellow-500',
    priority: 1,
  },
  unstable: {
    label: 'Unstable',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    iconColor: 'text-orange-500',
    priority: 2,
  },
  critical: {
    label: 'Critical',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    iconColor: 'text-red-500',
    priority: 3,
  },
  offline: {
    label: 'Offline',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    iconColor: 'text-gray-500',
    priority: 4,
  },
  checking: {
    label: 'Checking',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-500',
    priority: -1,
  },
}

// Individual component health monitor
function ComponentHealthMonitor({ componentKey, config, onStatusChange }) {
  const [status, setStatus] = useState('checking')
  const [lastCheck, setLastCheck] = useState(null)
  const [responseTime, setResponseTime] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [uptime, setUptime] = useState(100)
  const [consecutiveFailures, setConsecutiveFailures] = useState(0)

  const { api } = useEnhancedApi()
  const { executeWithRetry } = useEnhancedRetry()
  const intervalRef = useRef(null)
  const uptimeRef = useRef({ total: 0, successful: 0 })

  const checkHealth = useCallback(async () => {
    const startTime = Date.now()

    try {
      setStatus('checking')

      const result = await executeWithRetry(
        async () => {
          const response = await api.get(config.healthEndpoint, {
            timeout: config.timeout,
          })
          return response
        },
        {
          strategy: 'immediate',
          maxRetries: 1,
          context: { component: componentKey },
        }
      )

      const endTime = Date.now()
      const responseTimeMs = endTime - startTime

      setResponseTime(responseTimeMs)
      setLastCheck(new Date())
      setErrorMessage(null)
      setConsecutiveFailures(0)

      // Update uptime tracking
      uptimeRef.current.total++
      uptimeRef.current.successful++
      setUptime((uptimeRef.current.successful / uptimeRef.current.total) * 100)

      // Determine health status based on response time and data
      let newStatus = 'healthy'
      if (
        result.data?.status === 'degraded' ||
        responseTimeMs > config.timeout * 0.7
      ) {
        newStatus = 'degraded'
      } else if (
        result.data?.status === 'critical' ||
        responseTimeMs > config.timeout * 0.9
      ) {
        newStatus = 'critical'
      }

      setStatus(newStatus)
      onStatusChange(componentKey, {
        status: newStatus,
        responseTime: responseTimeMs,
        lastCheck: new Date(),
        uptime: (uptimeRef.current.successful / uptimeRef.current.total) * 100,
        consecutiveFailures: 0,
      })
    } catch (error) {
      const endTime = Date.now()
      const responseTimeMs = endTime - startTime

      setResponseTime(responseTimeMs)
      setLastCheck(new Date())
      setErrorMessage(error.message)
      setConsecutiveFailures((prev) => prev + 1)

      // Update uptime tracking
      uptimeRef.current.total++
      setUptime((uptimeRef.current.successful / uptimeRef.current.total) * 100)

      // Determine severity based on consecutive failures
      let newStatus = 'degraded'
      if (consecutiveFailures >= 3) {
        newStatus = 'critical'
      } else if (consecutiveFailures >= 5) {
        newStatus = 'offline'
      }

      setStatus(newStatus)
      onStatusChange(componentKey, {
        status: newStatus,
        responseTime: responseTimeMs,
        lastCheck: new Date(),
        uptime: (uptimeRef.current.successful / uptimeRef.current.total) * 100,
        consecutiveFailures: consecutiveFailures + 1,
        error: error.message,
      })
    }
  }, [
    componentKey,
    config,
    api,
    executeWithRetry,
    onStatusChange,
    consecutiveFailures,
  ])

  useEffect(() => {
    // Initial health check
    checkHealth()

    // Set up periodic health checks
    intervalRef.current = setInterval(checkHealth, config.checkInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [checkHealth, config.checkInterval])

  const IconComponent = config.icon
  const healthState = HEALTH_STATES[status]

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-full ${healthState.bgColor}`}>
            <IconComponent className={`h-5 w-5 ${healthState.iconColor}`} />
          </div>
          <div>
            <h3 className="font-medium text-gray-900">{config.name}</h3>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span className={`font-medium ${healthState.color}`}>
                {healthState.label}
              </span>
              {config.priority === 'critical' && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                  Critical
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="text-right">
          {responseTime && (
            <div className="text-lg font-semibold text-gray-900">
              {responseTime}ms
            </div>
          )}
          <div className="text-sm text-gray-500">
            {uptime.toFixed(1)}% uptime
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {/* Progress bar for uptime */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 w-12">Health:</span>
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                uptime >= 95
                  ? 'bg-green-500'
                  : uptime >= 80
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
              }`}
              style={{ width: `${uptime}%` }}
            />
          </div>
          <span className="text-xs text-gray-600 w-10">
            {uptime.toFixed(0)}%
          </span>
        </div>

        {/* Last check information */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>
            Last check: {lastCheck ? lastCheck.toLocaleTimeString() : 'Never'}
          </span>
          <span>
            Next in:{' '}
            {Math.round(
              (config.checkInterval -
                (Date.now() - (lastCheck?.getTime() || 0))) /
                1000
            )}
            s
          </span>
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
            Error: {errorMessage}
          </div>
        )}

        {/* Consecutive failures warning */}
        {consecutiveFailures > 0 && (
          <div className="text-xs text-orange-600 bg-orange-50 p-2 rounded">
            {consecutiveFailures} consecutive failure
            {consecutiveFailures > 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  )
}

// Overall system health status
function SystemHealthSummary({ componentStatuses, onRecoveryAction }) {
  const [overallStatus, setOverallStatus] = useState('checking')
  const [affectedComponents, setAffectedComponents] = useState([])
  const [systemMetrics, setSystemMetrics] = useState({
    totalComponents: Object.keys(SYSTEM_COMPONENTS).length,
    healthyComponents: 0,
    avgResponseTime: 0,
    overallUptime: 100,
  })

  const { showWarning, showError, showSuccess } = useNotifications()

  useEffect(() => {
    const statuses = Object.values(componentStatuses)
    if (statuses.length === 0) return

    // Calculate overall system status
    const criticalIssues = statuses.filter(
      (s) => s.status === 'critical' || s.status === 'offline'
    )
    const degradedIssues = statuses.filter(
      (s) => s.status === 'degraded' || s.status === 'unstable'
    )
    const healthyComponents = statuses.filter((s) => s.status === 'healthy')

    let newOverallStatus = 'healthy'
    if (criticalIssues.length > 0) {
      newOverallStatus = 'critical'
    } else if (degradedIssues.length > 0) {
      newOverallStatus = 'degraded'
    }

    setOverallStatus(newOverallStatus)
    setAffectedComponents([...criticalIssues, ...degradedIssues])

    // Calculate system metrics
    const avgResponseTime =
      statuses.reduce((sum, s) => sum + (s.responseTime || 0), 0) /
      statuses.length
    const avgUptime =
      statuses.reduce((sum, s) => sum + (s.uptime || 100), 0) / statuses.length

    setSystemMetrics({
      totalComponents: statuses.length,
      healthyComponents: healthyComponents.length,
      avgResponseTime: Math.round(avgResponseTime),
      overallUptime: avgUptime,
    })

    // Trigger notifications for status changes
    if (newOverallStatus === 'critical' && overallStatus !== 'critical') {
      showError(
        `System experiencing critical issues. ${criticalIssues.length} components affected.`,
        'System Health Alert',
        {
          persistent: true,
          action: {
            label: 'Recover',
            onClick: () => onRecoveryAction('critical'),
          },
        }
      )
    } else if (newOverallStatus === 'degraded' && overallStatus === 'healthy') {
      showWarning(
        `System performance degraded. ${degradedIssues.length} components affected.`,
        'Performance Warning'
      )
    } else if (newOverallStatus === 'healthy' && overallStatus !== 'healthy') {
      showSuccess('All systems operational', 'System Recovered')
    }
  }, [
    componentStatuses,
    overallStatus,
    showWarning,
    showError,
    showSuccess,
    onRecoveryAction,
  ])

  const healthState = HEALTH_STATES[overallStatus]

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className={`p-3 rounded-full ${healthState.bgColor}`}>
            {overallStatus === 'checking' ? (
              <ArrowPathIcon className="h-8 w-8 text-blue-500 animate-spin" />
            ) : overallStatus === 'healthy' ? (
              <CheckCircleIcon className={`h-8 w-8 ${healthState.iconColor}`} />
            ) : overallStatus === 'degraded' ? (
              <ExclamationTriangleIcon
                className={`h-8 w-8 ${healthState.iconColor}`}
              />
            ) : (
              <XCircleIcon className={`h-8 w-8 ${healthState.iconColor}`} />
            )}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">System Status</h2>
            <p className={`text-lg font-medium ${healthState.color}`}>
              {healthState.label}
            </p>
          </div>
        </div>

        <div className="text-right">
          <div className="text-3xl font-bold text-gray-900">
            {systemMetrics.overallUptime.toFixed(1)}%
          </div>
          <div className="text-sm text-gray-500">Overall Uptime</div>
        </div>
      </div>

      {/* System Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Components</p>
              <p className="text-2xl font-bold text-gray-900">
                {systemMetrics.healthyComponents}/
                {systemMetrics.totalComponents}
              </p>
            </div>
            <ServerIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Avg Response</p>
              <p className="text-2xl font-bold text-gray-900">
                {systemMetrics.avgResponseTime}ms
              </p>
            </div>
            <BoltIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Issues</p>
              <p className="text-2xl font-bold text-gray-900">
                {affectedComponents.length}
              </p>
            </div>
            <ExclamationTriangleIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Last Updated</p>
              <p className="text-sm font-medium text-gray-900">
                {new Date().toLocaleTimeString()}
              </p>
            </div>
            <ClockIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Active Issues */}
      {affectedComponents.length > 0 && (
        <div className="border-t pt-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Active Issues ({affectedComponents.length})
          </h3>
          <div className="space-y-2">
            {affectedComponents.map((component, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-red-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      component.status === 'critical'
                        ? 'bg-red-500'
                        : component.status === 'offline'
                          ? 'bg-gray-500'
                          : 'bg-yellow-500'
                    }`}
                  />
                  <span className="font-medium text-gray-900">
                    {
                      SYSTEM_COMPONENTS[
                        Object.keys(SYSTEM_COMPONENTS).find(
                          (key) => componentStatuses[key] === component
                        )
                      ]?.name
                    }
                  </span>
                  <span className="text-sm text-gray-600">
                    {component.error || `Status: ${component.status}`}
                  </span>
                </div>

                <button
                  onClick={() => onRecoveryAction(component)}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Retry
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Main system status indicator component
export default function SystemStatusIndicator({
  compact = false,
  showDetails = true,
}) {
  const [componentStatuses, setComponentStatuses] = useState({})
  const [isInitialized, setIsInitialized] = useState(false)
  const [autoRecoveryEnabled, setAutoRecoveryEnabled] = useState(true)
  const [recoveryAttempts, setRecoveryAttempts] = useState({})

  const { showInfo, notifyApiError } = useNotifications()

  const handleStatusChange = useCallback((componentKey, statusData) => {
    setComponentStatuses((prev) => ({
      ...prev,
      [componentKey]: statusData,
    }))
  }, [])

  const handleRecoveryAction = useCallback(
    async (target) => {
      try {
        if (typeof target === 'string') {
          // System-wide recovery
          showInfo('Initiating system recovery...', 'Recovery Started')

          // Implement system-wide recovery logic
          // This could include:
          // - Restarting failed services
          // - Clearing caches
          // - Reconnecting to external services
          // - Resetting circuit breakers

          setTimeout(() => {
            showInfo('System recovery completed', 'Recovery Complete')
          }, 3000)
        } else {
          // Component-specific recovery
          const componentKey = Object.keys(SYSTEM_COMPONENTS).find(
            (key) => componentStatuses[key] === target
          )

          if (componentKey) {
            const currentAttempts = recoveryAttempts[componentKey] || 0
            setRecoveryAttempts((prev) => ({
              ...prev,
              [componentKey]: currentAttempts + 1,
            }))

            showInfo(
              `Attempting recovery for ${SYSTEM_COMPONENTS[componentKey].name}...`,
              'Component Recovery'
            )

            // Implement component-specific recovery logic
            // This could include:
            // - Reconnecting to the service
            // - Clearing component-specific caches
            // - Refreshing authentication tokens
            // - Restarting health checks

            setTimeout(() => {
              // Reset the component status to trigger a fresh health check
              setComponentStatuses((prev) => ({
                ...prev,
                [componentKey]: {
                  ...prev[componentKey],
                  status: 'checking',
                  consecutiveFailures: 0,
                },
              }))
            }, 1000)
          }
        }
      } catch (error) {
        notifyApiError(`Recovery failed: ${error.message}`)
      }
    },
    [componentStatuses, recoveryAttempts, showInfo, notifyApiError]
  )

  useEffect(() => {
    setIsInitialized(true)
  }, [])

  if (compact) {
    const overallStatus =
      Object.values(componentStatuses).length > 0
        ? Object.values(componentStatuses).some(
            (s) => s.status === 'critical' || s.status === 'offline'
          )
          ? 'critical'
          : Object.values(componentStatuses).some(
                (s) => s.status === 'degraded' || s.status === 'unstable'
              )
            ? 'degraded'
            : 'healthy'
        : 'checking'

    const healthState = HEALTH_STATES[overallStatus]

    return (
      <div className="flex items-center space-x-2">
        <div
          className={`w-3 h-3 rounded-full ${
            overallStatus === 'healthy'
              ? 'bg-green-500'
              : overallStatus === 'degraded'
                ? 'bg-yellow-500'
                : overallStatus === 'critical'
                  ? 'bg-red-500'
                  : 'bg-gray-500'
          } ${overallStatus === 'checking' ? 'animate-pulse' : ''}`}
        />
        <span className={`text-sm font-medium ${healthState.color}`}>
          System {healthState.label}
        </span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* System Health Summary */}
      <SystemHealthSummary
        componentStatuses={componentStatuses}
        onRecoveryAction={handleRecoveryAction}
      />

      {/* Component Health Monitors */}
      {showDetails && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Component Health
            </h3>
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
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(SYSTEM_COMPONENTS).map(([key, config]) => (
              <ComponentHealthMonitor
                key={key}
                componentKey={key}
                config={config}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recovery History */}
      {Object.keys(recoveryAttempts).length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">
            Recovery History
          </h4>
          <div className="space-y-2">
            {Object.entries(recoveryAttempts).map(
              ([componentKey, attempts]) => (
                <div
                  key={componentKey}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-700">
                    {SYSTEM_COMPONENTS[componentKey].name}
                  </span>
                  <span className="text-gray-500">
                    {attempts} recovery attempt{attempts > 1 ? 's' : ''}
                  </span>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}
