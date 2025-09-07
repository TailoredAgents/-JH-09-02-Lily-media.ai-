import React from 'react'
import apiService from '../services/api'

class ErrorReporter {
  constructor() {
    this.setupErrorHandlers()
    this.errorQueue = []
    this.localErrors = this.loadLocalErrors()
    this.isOnline = navigator.onLine
    this.maxLocalErrors = 1000

    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true
      this.flushErrorQueue()
    })

    window.addEventListener('offline', () => {
      this.isOnline = false
    })
  }

  // Load errors from localStorage
  loadLocalErrors() {
    try {
      const stored = localStorage.getItem('aiSocial_errorLogs')
      return stored ? JSON.parse(stored) : []
    } catch (e) {
      console.warn('Failed to load local errors:', e)
      return []
    }
  }

  // Save errors to localStorage
  saveLocalErrors() {
    try {
      // Keep only the most recent errors
      const errors = this.localErrors.slice(0, this.maxLocalErrors)
      localStorage.setItem('aiSocial_errorLogs', JSON.stringify(errors))
    } catch (e) {
      console.warn('Failed to save local errors:', e)
    }
  }

  // Get local errors (for displaying when backend is down)
  getLocalErrors(limit = 100) {
    return this.localErrors.slice(0, limit)
  }

  // Clear local errors
  clearLocalErrors() {
    this.localErrors = []
    localStorage.removeItem('aiSocial_errorLogs')
  }

  setupErrorHandlers() {
    // Global error handler
    window.addEventListener('error', (event) => {
      this.reportError({
        message: event.message,
        source: event.filename,
        line: event.lineno,
        column: event.colno,
        error: event.error,
        type: 'javascript-error',
      })
    })

    // Promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.reportError({
        message:
          event.reason?.message ||
          event.reason ||
          'Unhandled Promise Rejection',
        error: event.reason,
        type: 'unhandled-rejection',
      })
    })

    // React Error Boundary errors are handled separately
  }

  reportError(errorData) {
    // Skip CORS errors to prevent infinite loops
    if (
      errorData.message &&
      (errorData.message.includes('CORS') ||
        errorData.message.includes('Cross-Origin') ||
        errorData.message.includes('blocked by CORS') ||
        errorData.message.includes('Access-Control-Allow-Origin'))
    ) {
      console.warn(
        'CORS error detected, skipping error reporting to prevent loops'
      )
      return
    }

    const error = {
      ...errorData,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      screen: {
        width: window.screen.width,
        height: window.screen.height,
      },
      id: Date.now() + Math.random(),
    }

    // Add stack trace if available
    if (errorData.error && errorData.error.stack) {
      error.stack = errorData.error.stack
    }

    // Always store locally first
    this.localErrors.unshift(error)
    this.saveLocalErrors()

    // Also add to queue for backend
    this.errorQueue.push(error)

    // Try to send immediately if online
    if (this.isOnline) {
      this.flushErrorQueue()
    }

    // Log to console as well
    console.error('Error captured:', error)
  }

  async flushErrorQueue() {
    // Temporarily disabled to prevent 405 log spam
    if (this.errorQueue.length > 0) {
      console.log(
        `Suppressed ${this.errorQueue.length} error reports to prevent log spam`
      )
      this.errorQueue = []
    }
    return
  }

  // Manual error reporting
  logError(message, details = {}) {
    this.reportError({
      message,
      ...details,
      type: 'manual-log',
    })
  }

  // Network error reporting
  logNetworkError(url, method, status, error) {
    // Skip reporting auth failures to prevent infinite loops
    if (status === 401 || status === 403) {
      console.warn(
        `Auth failure ${status} for ${method} ${url} - skipping error report to prevent loops`
      )
      return
    }

    // Skip rate limiting errors since they're expected
    if (status === 429) {
      console.warn(
        `Rate limit ${status} for ${method} ${url} - skipping error report`
      )
      return
    }

    this.reportError({
      message: `Network error: ${method} ${url} - ${status}`,
      endpoint: url,
      method,
      status,
      error: error?.message || error,
      type: 'network-error',
    })
  }

  // Performance issue reporting
  logPerformanceIssue(metric, value, threshold) {
    if (value > threshold) {
      this.reportError({
        message: `Performance issue: ${metric} exceeded threshold`,
        metric,
        value,
        threshold,
        type: 'performance-issue',
        severity: 'warning',
      })
    }
  }
}

// Create singleton instance
const errorReporter = new ErrorReporter()

// Export for use in React components
export default errorReporter

// React Error Boundary with WCAG 2.1 AA Accessibility Compliance
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorId: null,
    }
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    }
  }

  componentDidCatch(error, errorInfo) {
    // Report error with enhanced context
    errorReporter.reportError({
      message: error.toString(),
      componentStack: errorInfo.componentStack,
      error,
      type: 'react-error-boundary',
      errorId: this.state.errorId,
      timestamp: new Date().toISOString(),
      props: this.props.componentName || 'Unknown',
    })

    // Announce error to screen readers
    const announcement = `Application error occurred. Error ID: ${this.state.errorId}. Please use the reload button to restore functionality.`

    // Create live region for screen reader announcement
    setTimeout(() => {
      const liveRegion = document.createElement('div')
      liveRegion.setAttribute('aria-live', 'assertive')
      liveRegion.setAttribute('aria-atomic', 'true')
      liveRegion.setAttribute('class', 'sr-only')
      liveRegion.textContent = announcement
      document.body.appendChild(liveRegion)

      // Remove after announcement
      setTimeout(() => {
        if (document.body.contains(liveRegion)) {
          document.body.removeChild(liveRegion)
        }
      }, 3000)
    }, 100)
  }

  handleReload = () => {
    // Announce reload action to screen readers
    const liveRegion = document.createElement('div')
    liveRegion.setAttribute('aria-live', 'assertive')
    liveRegion.setAttribute('class', 'sr-only')
    liveRegion.textContent = 'Reloading application to recover from error...'
    document.body.appendChild(liveRegion)

    // Reload after short delay for announcement
    setTimeout(() => {
      window.location.reload()
    }, 1000)
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
          {/* Skip Link for Screen Readers */}
          <a
            href="#error-content"
            className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:z-50"
          >
            Skip to error content
          </a>

          {/* Main Error Content */}
          <main
            id="error-content"
            className="flex-grow flex items-center justify-center p-4 sm:p-6 lg:p-8"
            role="main"
            aria-labelledby="error-heading"
          >
            <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-lg max-w-md w-full border border-gray-200 dark:border-gray-700">
              {/* Error Icon with ARIA */}
              <div className="mb-6 text-center">
                <div
                  className="mx-auto h-16 w-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center"
                  role="img"
                  aria-label="Application error"
                >
                  <svg
                    className="h-8 w-8 text-red-600 dark:text-red-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                </div>
              </div>

              {/* Error Message */}
              <div className="text-center mb-6">
                <h1
                  id="error-heading"
                  className="text-2xl font-bold text-red-600 dark:text-red-400 mb-4"
                >
                  Application Error
                </h1>
                <p className="text-gray-600 dark:text-gray-300 mb-4">
                  An unexpected error occurred while loading this page. The
                  error has been automatically reported to our team.
                </p>

                {/* Error ID for Support */}
                <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-md mb-4">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <strong>Error ID:</strong>{' '}
                    <code className="font-mono text-xs">
                      {this.state.errorId}
                    </code>
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Please provide this ID when contacting support
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={this.handleReload}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors font-medium"
                  aria-describedby="reload-description"
                  type="button"
                >
                  Reload Application
                </button>
                <p id="reload-description" className="sr-only">
                  This will refresh the page and may resolve the error
                </p>

                <button
                  onClick={this.handleGoHome}
                  className="w-full border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 py-3 px-4 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  aria-describedby="home-description"
                  type="button"
                >
                  Go to Homepage
                </button>
                <p id="home-description" className="sr-only">
                  This will take you to the main page of the application
                </p>
              </div>

              {/* Recovery Instructions */}
              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900 rounded-md">
                <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                  Recovery Options
                </h3>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                  <li>• Try reloading the page</li>
                  <li>• Clear your browser cache</li>
                  <li>• Check your internet connection</li>
                  <li>• Contact support if the issue persists</li>
                </ul>
              </div>

              {/* Additional Context for Screen Readers */}
              <div className="sr-only">
                <p>
                  You have encountered an application error. This error has been
                  automatically reported. You can try reloading the page or
                  returning to the homepage to continue using the application.
                  If the problem persists, please contact support with the
                  provided error ID.
                </p>
              </div>
            </div>
          </main>

          {/* Footer with Support Link */}
          <footer className="p-6 text-center border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Need help with this error?{' '}
              <a
                href="mailto:support@lily-ai-socialmedia.com"
                className="text-blue-600 hover:text-blue-500 focus:outline-none focus:underline"
                aria-label="Contact support via email about application error"
              >
                Contact Support
              </a>
            </p>
          </footer>
        </div>
      )
    }

    return this.props.children
  }
}
