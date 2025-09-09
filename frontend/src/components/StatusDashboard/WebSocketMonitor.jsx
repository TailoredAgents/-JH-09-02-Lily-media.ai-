import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  WifiIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  BoltIcon,
  SignalIcon,
  ClockIcon,
  ChartBarIcon,
  PauseIcon,
  PlayIcon,
} from '@heroicons/react/24/outline'
import { useNotifications } from '../../hooks/useNotifications'

const CONNECTION_STATES = {
  connecting: {
    label: 'Connecting',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: ArrowPathIcon,
    animate: true,
  },
  connected: {
    label: 'Connected',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    icon: CheckCircleIcon,
    animate: false,
  },
  disconnected: {
    label: 'Disconnected',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: XCircleIcon,
    animate: false,
  },
  reconnecting: {
    label: 'Reconnecting',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    icon: ArrowPathIcon,
    animate: true,
  },
  error: {
    label: 'Error',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: ExclamationTriangleIcon,
    animate: false,
  },
}

// WebSocket connection manager hook
function useWebSocketMonitor() {
  const [connectionState, setConnectionState] = useState('disconnected')
  const [lastMessage, setLastMessage] = useState(null)
  const [messageCount, setMessageCount] = useState(0)
  const [latency, setLatency] = useState(0)
  const [errorCount, setErrorCount] = useState(0)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [isAutoReconnectEnabled, setIsAutoReconnectEnabled] = useState(true)
  const [connectionQuality, setConnectionQuality] = useState('good')
  
  const wsRef = useRef(null)
  const pingIntervalRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const lastPingRef = useRef(null)
  const metricsRef = useRef({
    messagesPerSecond: 0,
    avgLatency: 0,
    uptime: 0,
    startTime: null,
  })

  const { showWarning, showError, showSuccess, showInfo } = useNotifications()

  const calculateConnectionQuality = useCallback((currentLatency, errorRate) => {
    if (errorRate > 10 || currentLatency > 1000) return 'poor'
    if (errorRate > 5 || currentLatency > 500) return 'fair' 
    return 'good'
  }, [])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setConnectionState('connecting')
    setReconnectAttempts(prev => prev + 1)
    
    try {
      // Use secure WebSocket in production
      const wsUrl = process.env.NODE_ENV === 'production' 
        ? 'wss://your-api-domain.com/ws' 
        : 'ws://localhost:8000/ws'
      
      wsRef.current = new WebSocket(wsUrl)
      
      wsRef.current.onopen = () => {
        setConnectionState('connected')
        setErrorCount(0)
        setReconnectAttempts(0)
        metricsRef.current.startTime = Date.now()
        
        showSuccess('WebSocket connected', 'Connection Status')
        
        // Start ping/pong for latency monitoring
        startLatencyMonitoring()
      }

      wsRef.current.onmessage = (event) => {
        setLastMessage({
          data: event.data,
          timestamp: new Date(),
        })
        setMessageCount(prev => prev + 1)
        
        // Handle pong responses for latency calculation
        if (event.data === 'pong' && lastPingRef.current) {
          const currentLatency = Date.now() - lastPingRef.current
          setLatency(currentLatency)
          
          // Update average latency
          metricsRef.current.avgLatency = 
            (metricsRef.current.avgLatency + currentLatency) / 2
          
          // Update connection quality
          const errorRate = (errorCount / messageCount) * 100
          setConnectionQuality(calculateConnectionQuality(currentLatency, errorRate))
        }
      }

      wsRef.current.onclose = (event) => {
        setConnectionState('disconnected')
        clearInterval(pingIntervalRef.current)
        
        if (event.wasClean) {
          showInfo('WebSocket disconnected', 'Connection Status')
        } else {
          showWarning('WebSocket connection lost', 'Connection Status')
          
          if (isAutoReconnectEnabled) {
            setConnectionState('reconnecting')
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
            
            reconnectTimeoutRef.current = setTimeout(() => {
              connect()
            }, delay)
          }
        }
      }

      wsRef.current.onerror = (error) => {
        setConnectionState('error')
        setErrorCount(prev => prev + 1)
        showError('WebSocket connection error', 'Connection Error')
      }

    } catch (error) {
      setConnectionState('error')
      setErrorCount(prev => prev + 1)
      showError(`Failed to connect: ${error.message}`, 'Connection Error')
    }
  }, [reconnectAttempts, isAutoReconnectEnabled, showSuccess, showInfo, showWarning, showError, calculateConnectionQuality, errorCount, messageCount])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    clearInterval(pingIntervalRef.current)
    clearTimeout(reconnectTimeoutRef.current)
    setConnectionState('disconnected')
  }, [])

  const startLatencyMonitoring = useCallback(() => {
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        lastPingRef.current = Date.now()
        wsRef.current.send('ping')
      }
    }, 5000)
  }, [])

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message)
      return true
    }
    return false
  }, [])

  // Calculate uptime
  useEffect(() => {
    if (connectionState === 'connected' && metricsRef.current.startTime) {
      const interval = setInterval(() => {
        metricsRef.current.uptime = Date.now() - metricsRef.current.startTime
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [connectionState])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearInterval(pingIntervalRef.current)
      clearTimeout(reconnectTimeoutRef.current)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return {
    connectionState,
    lastMessage,
    messageCount,
    latency,
    errorCount,
    reconnectAttempts,
    connectionQuality,
    metrics: metricsRef.current,
    isAutoReconnectEnabled,
    setIsAutoReconnectEnabled,
    connect,
    disconnect,
    sendMessage,
  }
}

// WebSocket metrics component
function WebSocketMetrics({ metrics, connectionState, latency, connectionQuality }) {
  const formatUptime = (milliseconds) => {
    const seconds = Math.floor(milliseconds / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`
    return `${seconds}s`
  }

  const getQualityColor = (quality) => {
    switch (quality) {
      case 'good': return 'text-green-600'
      case 'fair': return 'text-yellow-600'  
      case 'poor': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Latency</p>
            <p className="text-2xl font-bold text-gray-900">{latency}ms</p>
          </div>
          <BoltIcon className="h-8 w-8 text-blue-400" />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Quality</p>
            <p className={`text-lg font-bold capitalize ${getQualityColor(connectionQuality)}`}>
              {connectionQuality}
            </p>
          </div>
          <SignalIcon className="h-8 w-8 text-green-400" />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Messages/Min</p>
            <p className="text-2xl font-bold text-gray-900">
              {Math.round(metrics.messagesPerSecond * 60)}
            </p>
          </div>
          <ChartBarIcon className="h-8 w-8 text-purple-400" />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Uptime</p>
            <p className="text-lg font-bold text-gray-900">
              {connectionState === 'connected' ? formatUptime(metrics.uptime) : '0s'}
            </p>
          </div>
          <ClockIcon className="h-8 w-8 text-indigo-400" />
        </div>
      </div>
    </div>
  )
}

// Main WebSocket monitor component
export default function WebSocketMonitor({ compact = false, autoConnect = true }) {
  const {
    connectionState,
    lastMessage,
    messageCount,
    latency,
    errorCount,
    reconnectAttempts,
    connectionQuality,
    metrics,
    isAutoReconnectEnabled,
    setIsAutoReconnectEnabled,
    connect,
    disconnect,
    sendMessage,
  } = useWebSocketMonitor()

  const [testMessage, setTestMessage] = useState('')
  const [showDetails, setShowDetails] = useState(!compact)

  useEffect(() => {
    if (autoConnect && connectionState === 'disconnected') {
      connect()
    }
  }, [autoConnect, connectionState, connect])

  const state = CONNECTION_STATES[connectionState]
  const IconComponent = state.icon

  if (compact) {
    return (
      <div 
        className="flex items-center space-x-3"
        role="status"
        aria-label={`WebSocket connection status: ${state.label}`}
      >
        <div className={`p-2 rounded-full ${state.bgColor}`}>
          <IconComponent 
            className={`h-4 w-4 ${state.color} ${state.animate ? 'animate-spin' : ''}`}
            aria-hidden="true" 
          />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">WebSocket</p>
          <p className={`text-xs ${state.color}`}>{state.label}</p>
        </div>
        {connectionState === 'connected' && (
          <div className="text-xs text-gray-500">
            <div>↕ {latency}ms</div>
            <div>✓ {messageCount}</div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Connection Status Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${state.bgColor}`}>
              <IconComponent 
                className={`h-8 w-8 ${state.color} ${state.animate ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">WebSocket Monitor</h2>
              <p className={`text-lg font-medium ${state.color}`}>
                {state.label}
                {reconnectAttempts > 0 && connectionState !== 'connected' && (
                  <span className="ml-2 text-sm text-gray-500">
                    (Attempt {reconnectAttempts})
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={isAutoReconnectEnabled}
                onChange={(e) => setIsAutoReconnectEnabled(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Auto Reconnect</span>
            </label>

            {connectionState === 'connected' ? (
              <button
                onClick={disconnect}
                className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                type="button"
              >
                <PauseIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                Disconnect
              </button>
            ) : (
              <button
                onClick={connect}
                className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                type="button"
              >
                <PlayIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                Connect
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <WebSocketMetrics
        metrics={metrics}
        connectionState={connectionState}
        latency={latency}
        connectionQuality={connectionQuality}
      />

      {showDetails && (
        <>
          {/* Connection Details */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Connection Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Connection Statistics
                  </label>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Messages Received:</span>
                      <span className="text-sm font-medium text-gray-900">{messageCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Error Count:</span>
                      <span className="text-sm font-medium text-red-600">{errorCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Reconnect Attempts:</span>
                      <span className="text-sm font-medium text-orange-600">{reconnectAttempts}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Avg Latency:</span>
                      <span className="text-sm font-medium text-blue-600">
                        {Math.round(metrics.avgLatency)}ms
                      </span>
                    </div>
                  </div>
                </div>

                {/* Test Message Sender */}
                {connectionState === 'connected' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Test Message
                    </label>
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={testMessage}
                        onChange={(e) => setTestMessage(e.target.value)}
                        placeholder="Enter test message"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <button
                        onClick={() => {
                          if (sendMessage(testMessage)) {
                            setTestMessage('')
                          }
                        }}
                        disabled={!testMessage.trim()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        type="button"
                      >
                        Send
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Last Message */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Last Message Received
                </label>
                <div className="bg-gray-50 rounded-lg p-4">
                  {lastMessage ? (
                    <div className="space-y-2">
                      <div className="text-xs text-gray-500">
                        {lastMessage.timestamp.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-900 font-mono bg-white p-2 rounded border">
                        {lastMessage.data}
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500 italic">
                      No messages received yet
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}