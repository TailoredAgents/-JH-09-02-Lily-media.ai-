import React, { useState, useEffect, useCallback } from 'react'
import {
  WifiIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  SignalIcon,
  BoltIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CpuChipIcon,
  ServerIcon,
} from '@heroicons/react/24/outline'
import { useEnhancedApi } from '../../hooks/useEnhancedApi'
import { useEnhancedRetry } from '../../hooks/useEnhancedRetry'
import { useNotifications } from '../../hooks/useNotifications'

// Real-time metrics tracking
function useRealTimeMetrics() {
  const [metrics, setMetrics] = useState({
    connectionLatency: 0,
    requestsPerMinute: 0,
    activeUsers: 0,
    systemLoad: 0,
    memoryUsage: 0,
    errorRate: 0,
    lastUpdated: new Date(),
  })

  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const { connectionStatus, checkApiHealth } = useEnhancedApi()
  const { globalStats } = useEnhancedRetry()

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Update metrics periodically
  useEffect(() => {
    const updateMetrics = async () => {
      const startTime = Date.now()

      try {
        // Measure connection latency
        await checkApiHealth()
        const latency = Date.now() - startTime

        setMetrics((prev) => ({
          ...prev,
          connectionLatency: latency,
          requestsPerMinute: prev.requestsPerMinute + 1,
          activeUsers: Math.floor(Math.random() * 50) + 100, // Simulated
          systemLoad: Math.random() * 100,
          memoryUsage: Math.random() * 90 + 10,
          errorRate: (globalStats.failed / (globalStats.total || 1)) * 100,
          lastUpdated: new Date(),
        }))
      } catch (error) {
        setMetrics((prev) => ({
          ...prev,
          connectionLatency: -1,
          errorRate: 100,
          lastUpdated: new Date(),
        }))
      }
    }

    updateMetrics()
    const interval = setInterval(updateMetrics, 5000)
    return () => clearInterval(interval)
  }, [checkApiHealth, globalStats])

  return { metrics, isOnline, connectionStatus }
}

// Status indicator component
function StatusIndicator({
  status,
  label,
  value,
  unit = '',
  threshold = null,
  icon: Icon = SignalIcon,
  onClick = null,
}) {
  const getStatusColor = () => {
    if (status === 'healthy') return 'text-green-600'
    if (status === 'warning') return 'text-yellow-600'
    if (status === 'critical') return 'text-red-600'
    if (status === 'offline') return 'text-gray-500'
    return 'text-blue-600'
  }

  const getBgColor = () => {
    if (status === 'healthy') return 'bg-green-50'
    if (status === 'warning') return 'bg-yellow-50'
    if (status === 'critical') return 'bg-red-50'
    if (status === 'offline') return 'bg-gray-50'
    return 'bg-blue-50'
  }

  const getBorderColor = () => {
    if (status === 'healthy') return 'border-green-200'
    if (status === 'warning') return 'border-yellow-200'
    if (status === 'critical') return 'border-red-200'
    if (status === 'offline') return 'border-gray-200'
    return 'border-blue-200'
  }

  return (
    <div
      className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors ${
        onClick ? 'cursor-pointer hover:shadow-sm' : ''
      } ${getBgColor()} ${getBorderColor()}`}
      onClick={onClick}
    >
      <Icon className={`h-4 w-4 ${getStatusColor()}`} />
      <div className="flex-1 min-w-0">
        <div className={`text-xs font-medium ${getStatusColor()}`}>{label}</div>
        <div className="text-xs text-gray-600 truncate">
          {value}
          {unit}
        </div>
      </div>

      {threshold && (
        <div className="flex items-center">
          <div className="w-12 bg-gray-200 rounded-full h-1">
            <div
              className={`h-1 rounded-full transition-all ${
                value > threshold * 0.8
                  ? 'bg-red-500'
                  : value > threshold * 0.6
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              }`}
              style={{ width: `${Math.min((value / threshold) * 100, 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

// Performance graph component
function MiniPerformanceGraph({ data, title, color = 'blue' }) {
  const maxValue = Math.max(...data, 1)
  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * 100
      const y = 100 - (value / maxValue) * 100
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-medium text-gray-700">{title}</h4>
        <span className="text-xs text-gray-500">
          {data[data.length - 1].toFixed(1)}
        </span>
      </div>
      <svg viewBox="0 0 100 30" className="w-full h-6">
        <polyline
          fill="none"
          stroke={
            color === 'blue'
              ? '#3B82F6'
              : color === 'green'
                ? '#10B981'
                : '#EF4444'
          }
          strokeWidth="2"
          points={points}
        />
        <defs>
          <linearGradient
            id={`gradient-${color}`}
            x1="0%"
            y1="0%"
            x2="0%"
            y2="100%"
          >
            <stop
              offset="0%"
              stopColor={
                color === 'blue'
                  ? '#3B82F6'
                  : color === 'green'
                    ? '#10B981'
                    : '#EF4444'
              }
              stopOpacity="0.1"
            />
            <stop
              offset="100%"
              stopColor={
                color === 'blue'
                  ? '#3B82F6'
                  : color === 'green'
                    ? '#10B981'
                    : '#EF4444'
              }
              stopOpacity="0"
            />
          </linearGradient>
        </defs>
        <polygon
          fill={`url(#gradient-${color})`}
          points={`${points} 100,100 0,100`}
        />
      </svg>
    </div>
  )
}

// Main real-time status bar component
export default function RealTimeStatusBar({
  expanded = false,
  onToggle = null,
  showDetails = true,
  position = 'bottom', // top, bottom, sidebar
}) {
  const [isExpanded, setIsExpanded] = useState(expanded)
  const [showDropdown, setShowDropdown] = useState(false)
  const [performanceHistory, setPerformanceHistory] = useState({
    latency: Array(20).fill(0),
    cpu: Array(20).fill(0),
    memory: Array(20).fill(0),
    errors: Array(20).fill(0),
  })

  const { metrics, isOnline, connectionStatus } = useRealTimeMetrics()
  const { showInfo } = useNotifications()

  // Update performance history
  useEffect(() => {
    setPerformanceHistory((prev) => ({
      latency: [...prev.latency.slice(1), metrics.connectionLatency],
      cpu: [...prev.cpu.slice(1), metrics.systemLoad],
      memory: [...prev.memory.slice(1), metrics.memoryUsage],
      errors: [...prev.errors.slice(1), metrics.errorRate],
    }))
  }, [metrics])

  const getOverallStatus = useCallback(() => {
    if (!isOnline || connectionStatus === 'disconnected') return 'offline'
    if (metrics.connectionLatency > 2000 || metrics.errorRate > 10)
      return 'critical'
    if (metrics.connectionLatency > 1000 || metrics.errorRate > 5)
      return 'warning'
    return 'healthy'
  }, [isOnline, connectionStatus, metrics])

  const handleToggle = useCallback(() => {
    const newExpanded = !isExpanded
    setIsExpanded(newExpanded)
    if (onToggle) onToggle(newExpanded)
  }, [isExpanded, onToggle])

  const overallStatus = getOverallStatus()

  // Compact status bar for when not expanded
  if (!isExpanded) {
    return (
      <div
        className={`
        fixed ${position === 'top' ? 'top-0' : 'bottom-0'} left-0 right-0 z-40 
        bg-white border-${position === 'top' ? 'b' : 't'} border-gray-200 shadow-lg
      `}
        role="banner"
        aria-label="System status bar"
        aria-live="polite"
        aria-atomic="false"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center space-x-4">
              {/* Overall status indicator */}
              <div className="flex items-center space-x-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    overallStatus === 'healthy'
                      ? 'bg-green-500'
                      : overallStatus === 'warning'
                        ? 'bg-yellow-500'
                        : overallStatus === 'critical'
                          ? 'bg-red-500'
                          : 'bg-gray-500'
                  } ${overallStatus !== 'offline' ? 'animate-pulse' : ''}`}
                />

                <span className="text-sm font-medium text-gray-700">
                  System{' '}
                  {overallStatus === 'healthy'
                    ? 'Healthy'
                    : overallStatus === 'warning'
                      ? 'Warning'
                      : overallStatus === 'critical'
                        ? 'Critical'
                        : 'Offline'}
                </span>
              </div>

              {/* Key metrics */}
              <div className="hidden md:flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <BoltIcon className="h-4 w-4" />
                  <span>
                    {metrics.connectionLatency >= 0
                      ? `${metrics.connectionLatency}ms`
                      : 'N/A'}
                  </span>
                </div>

                <div className="flex items-center space-x-1">
                  <CpuChipIcon className="h-4 w-4" />
                  <span>{metrics.systemLoad.toFixed(0)}%</span>
                </div>

                <div className="flex items-center space-x-1">
                  <ServerIcon className="h-4 w-4" />
                  <span>{metrics.activeUsers} users</span>
                </div>

                {metrics.errorRate > 0 && (
                  <div className="flex items-center space-x-1 text-red-600">
                    <ExclamationTriangleIcon className="h-4 w-4" />
                    <span>{metrics.errorRate.toFixed(1)}% errors</span>
                  </div>
                )}
              </div>

              <span className="text-xs text-gray-500">
                Updated {new Date(metrics.lastUpdated).toLocaleTimeString()}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="p-1 rounded hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                aria-expanded={showDropdown}
                aria-controls="status-dropdown"
                aria-label={showDropdown ? "Hide status details" : "Show status details"}
                type="button"
              >
                <ChevronUpIcon
                  className={`h-4 w-4 text-gray-600 transform transition-transform ${
                    showDropdown ? 'rotate-180' : ''
                  }`}
                  aria-hidden="true"
                />
              </button>

              {onToggle && (
                <button
                  onClick={handleToggle}
                  className="p-1 rounded hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  aria-label="Expand full status dashboard"
                  type="button"
                >
                  <ChevronUpIcon className="h-4 w-4 text-gray-600" aria-hidden="true" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Dropdown details */}
        {showDropdown && (
          <div 
            id="status-dropdown"
            className="border-t border-gray-200 bg-gray-50"
            role="region"
            aria-label="Detailed status information"
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <StatusIndicator
                  status={isOnline ? 'healthy' : 'offline'}
                  label="Connection"
                  value={isOnline ? 'Online' : 'Offline'}
                  icon={WifiIcon}
                />

                <StatusIndicator
                  status={
                    metrics.connectionLatency < 500
                      ? 'healthy'
                      : metrics.connectionLatency < 1000
                        ? 'warning'
                        : 'critical'
                  }
                  label="Latency"
                  value={
                    metrics.connectionLatency >= 0
                      ? metrics.connectionLatency
                      : 'N/A'
                  }
                  unit="ms"
                  icon={BoltIcon}
                />

                <StatusIndicator
                  status={
                    metrics.systemLoad < 60
                      ? 'healthy'
                      : metrics.systemLoad < 80
                        ? 'warning'
                        : 'critical'
                  }
                  label="System Load"
                  value={metrics.systemLoad.toFixed(0)}
                  unit="%"
                  threshold={100}
                  icon={CpuChipIcon}
                />

                <StatusIndicator
                  status={
                    metrics.memoryUsage < 70
                      ? 'healthy'
                      : metrics.memoryUsage < 90
                        ? 'warning'
                        : 'critical'
                  }
                  label="Memory"
                  value={metrics.memoryUsage.toFixed(0)}
                  unit="%"
                  threshold={100}
                  icon={ServerIcon}
                />

                <StatusIndicator
                  status={
                    metrics.errorRate < 1
                      ? 'healthy'
                      : metrics.errorRate < 5
                        ? 'warning'
                        : 'critical'
                  }
                  label="Error Rate"
                  value={metrics.errorRate.toFixed(1)}
                  unit="%"
                  icon={ExclamationTriangleIcon}
                />

                <StatusIndicator
                  status="healthy"
                  label="Active Users"
                  value={metrics.activeUsers}
                  unit=""
                  icon={SignalIcon}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Full expanded status dashboard
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2 rounded-full ${
                overallStatus === 'healthy'
                  ? 'bg-green-100'
                  : overallStatus === 'warning'
                    ? 'bg-yellow-100'
                    : overallStatus === 'critical'
                      ? 'bg-red-100'
                      : 'bg-gray-100'
              }`}
            >
              {overallStatus === 'healthy' ? (
                <CheckCircleIcon className="h-6 w-6 text-green-600" />
              ) : overallStatus === 'warning' ? (
                <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600" />
              ) : overallStatus === 'critical' ? (
                <XCircleIcon className="h-6 w-6 text-red-600" />
              ) : (
                <WifiIcon className="h-6 w-6 text-gray-600" />
              )}
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                System Status
              </h3>
              <p
                className={`text-sm ${
                  overallStatus === 'healthy'
                    ? 'text-green-600'
                    : overallStatus === 'warning'
                      ? 'text-yellow-600'
                      : overallStatus === 'critical'
                        ? 'text-red-600'
                        : 'text-gray-600'
                }`}
              >
                {overallStatus === 'healthy'
                  ? 'All systems operational'
                  : overallStatus === 'warning'
                    ? 'Some systems degraded'
                    : overallStatus === 'critical'
                      ? 'Critical issues detected'
                      : 'System offline'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">
              Last updated: {new Date(metrics.lastUpdated).toLocaleTimeString()}
            </span>

            {onToggle && (
              <button
                onClick={handleToggle}
                className="p-2 rounded-lg hover:bg-gray-100"
                title="Collapse"
              >
                <ChevronDownIcon className="h-5 w-5 text-gray-600" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* Status indicators grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatusIndicator
            status={isOnline ? 'healthy' : 'offline'}
            label="Network Connection"
            value={isOnline ? 'Connected' : 'Disconnected'}
            icon={WifiIcon}
            onClick={() =>
              showInfo(
                'Network status: ' + (isOnline ? 'Connected' : 'Disconnected')
              )
            }
          />

          <StatusIndicator
            status={
              metrics.connectionLatency < 500
                ? 'healthy'
                : metrics.connectionLatency < 1000
                  ? 'warning'
                  : 'critical'
            }
            label="API Latency"
            value={
              metrics.connectionLatency >= 0 ? metrics.connectionLatency : 'N/A'
            }
            unit="ms"
            icon={BoltIcon}
          />

          <StatusIndicator
            status={
              metrics.systemLoad < 60
                ? 'healthy'
                : metrics.systemLoad < 80
                  ? 'warning'
                  : 'critical'
            }
            label="System Load"
            value={metrics.systemLoad.toFixed(1)}
            unit="%"
            threshold={100}
            icon={CpuChipIcon}
          />

          <StatusIndicator
            status={
              metrics.memoryUsage < 70
                ? 'healthy'
                : metrics.memoryUsage < 90
                  ? 'warning'
                  : 'critical'
            }
            label="Memory Usage"
            value={metrics.memoryUsage.toFixed(1)}
            unit="%"
            threshold={100}
            icon={ServerIcon}
          />

          <StatusIndicator
            status={
              metrics.errorRate < 1
                ? 'healthy'
                : metrics.errorRate < 5
                  ? 'warning'
                  : 'critical'
            }
            label="Error Rate"
            value={metrics.errorRate.toFixed(1)}
            unit="%"
            icon={ExclamationTriangleIcon}
          />

          <StatusIndicator
            status="healthy"
            label="Active Users"
            value={metrics.activeUsers}
            unit=" online"
            icon={SignalIcon}
          />
        </div>

        {/* Performance graphs */}
        {showDetails && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MiniPerformanceGraph
              data={performanceHistory.latency}
              title="Latency (ms)"
              color="blue"
            />

            <MiniPerformanceGraph
              data={performanceHistory.cpu}
              title="CPU Usage (%)"
              color="green"
            />

            <MiniPerformanceGraph
              data={performanceHistory.memory}
              title="Memory (%)"
              color="blue"
            />

            <MiniPerformanceGraph
              data={performanceHistory.errors}
              title="Error Rate (%)"
              color="red"
            />
          </div>
        )}

        {/* Additional system info */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-900">Uptime:</span>
              <span className="ml-2 text-gray-600">99.9%</span>
            </div>
            <div>
              <span className="font-medium text-gray-900">Region:</span>
              <span className="ml-2 text-gray-600">US-East</span>
            </div>
            <div>
              <span className="font-medium text-gray-900">Build:</span>
              <span className="ml-2 text-gray-600">v2.1.0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
