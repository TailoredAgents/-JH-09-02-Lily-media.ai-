import React, { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  ExclamationCircleIcon, 
  HomeIcon, 
  ChevronLeftIcon,
  ArrowPathIcon 
} from '@heroicons/react/24/outline'

/**
 * WCAG 2.1 AA Compliant Generic Error Page
 * 
 * Handles various error states with proper accessibility:
 * - Server errors (500, 502, 503)
 * - Network errors
 * - Timeout errors
 * - Generic application errors
 * 
 * Accessibility Features:
 * - Proper heading hierarchy
 * - High contrast colors (4.5:1 minimum)
 * - Focus management
 * - Screen reader announcements
 * - Clear recovery options
 * - Semantic HTML with ARIA attributes
 */
const ErrorPage = ({ 
  errorCode = 'ERROR', 
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  showRetry = true 
}) => {
  const location = useLocation()
  
  // Get error details from router state or props
  const error = location.state?.error || {}
  const displayCode = error.status || errorCode
  const displayTitle = error.statusText || title
  const displayMessage = error.message || message

  useEffect(() => {
    // Set page title for browser and screen readers
    document.title = `Error ${displayCode} - Lily AI Social Media`
    
    // Announce error to screen readers with appropriate urgency
    const announcement = document.createElement('div')
    announcement.setAttribute('aria-live', 'assertive')
    announcement.setAttribute('aria-atomic', 'true')
    announcement.className = 'sr-only'
    announcement.textContent = `Error ${displayCode}: ${displayTitle}. ${displayMessage}`
    document.body.appendChild(announcement)

    // Focus on main heading for screen reader navigation
    const heading = document.getElementById('error-heading')
    if (heading) {
      heading.focus()
    }

    return () => {
      if (document.body.contains(announcement)) {
        document.body.removeChild(announcement)
      }
    }
  }, [displayCode, displayTitle, displayMessage])

  const handleRetry = () => {
    window.location.reload()
  }

  const getErrorIcon = () => {
    if (displayCode >= 500) {
      return 'text-red-600' // Server errors - critical
    } else if (displayCode >= 400) {
      return 'text-orange-600' // Client errors - warning
    }
    return 'text-red-600' // Default to critical
  }

  const getErrorBackground = () => {
    if (displayCode >= 500) {
      return 'bg-red-100' // Server errors
    } else if (displayCode >= 400) {
      return 'bg-orange-100' // Client errors
    }
    return 'bg-red-100' // Default
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* Error Icon */}
          <div className="flex justify-center mb-6">
            <div 
              className={`rounded-full ${getErrorBackground()} p-3`}
              role="img"
              aria-label={`Error ${displayCode} indicator`}
            >
              <ExclamationCircleIcon 
                className={`h-8 w-8 ${getErrorIcon()}`}
                aria-hidden="true"
              />
            </div>
          </div>

          {/* Error Content */}
          <div className="text-center">
            <h1 
              id="error-heading"
              className="text-3xl font-bold text-gray-900 mb-2 focus:outline-none"
              tabIndex={-1}
            >
              {displayCode} - {displayTitle}
            </h1>
            
            <h2 className="text-lg text-gray-700 mb-6">
              {displayMessage}
            </h2>

            {/* Error Details for Common Codes */}
            <div className="space-y-4 mb-8 text-left">
              {displayCode >= 500 && (
                <>
                  <p className="text-sm text-gray-600">
                    This is a server error. The issue is on our end and we're working to fix it.
                  </p>
                  <ul className="text-sm text-gray-600 space-y-2" role="list">
                    <li className="flex items-start">
                      <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                      <span>Try refreshing the page in a few minutes</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                      <span>Check our status page for known issues</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                      <span>Contact support if the problem persists</span>
                    </li>
                  </ul>
                </>
              )}

              {displayCode >= 400 && displayCode < 500 && (
                <>
                  <p className="text-sm text-gray-600">
                    This appears to be a client error. Please check the following:
                  </p>
                  <ul className="text-sm text-gray-600 space-y-2" role="list">
                    <li className="flex items-start">
                      <span className="text-orange-500 mr-2" aria-hidden="true">•</span>
                      <span>Verify your internet connection</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-orange-500 mr-2" aria-hidden="true">•</span>
                      <span>Clear your browser cache and cookies</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-orange-500 mr-2" aria-hidden="true">•</span>
                      <span>Try signing out and signing back in</span>
                    </li>
                  </ul>
                </>
              )}
            </div>

            {/* Recovery Actions */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                What you can do:
              </h3>
              
              <div className="space-y-3">
                {showRetry && (
                  <button
                    onClick={handleRetry}
                    className="w-full flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
                  >
                    <ArrowPathIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                    Try Again
                  </button>
                )}

                <Link
                  to="/"
                  className="w-full flex justify-center items-center px-4 py-2 border border-purple-300 rounded-md shadow-sm bg-white text-sm font-medium text-purple-700 hover:bg-purple-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
                >
                  <HomeIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                  Return to Home
                </Link>

                <button
                  onClick={() => window.history.back()}
                  className="w-full flex justify-center items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
                >
                  <ChevronLeftIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                  Go Back
                </button>
              </div>
            </div>

            {/* Support Section */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Still Need Help?
              </h3>
              <p className="text-xs text-gray-600 mb-3">
                If this error persists, our support team can help you resolve it.
              </p>
              <div className="flex flex-col sm:flex-row gap-2">
                <Link
                  to="/settings"
                  className="flex-1 text-center px-3 py-2 text-sm text-purple-600 hover:text-purple-500 underline focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 rounded"
                >
                  Contact Support
                </Link>
                <a
                  href="https://status.lily-ai-socialmedia.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-center px-3 py-2 text-sm text-purple-600 hover:text-purple-500 underline focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 rounded"
                >
                  Status Page
                </a>
              </div>
            </div>

            {/* Technical Details (for development) */}
            {process.env.NODE_ENV === 'development' && error.stack && (
              <details className="mt-6 pt-4 border-t border-gray-200 text-left">
                <summary className="text-sm font-medium text-gray-900 cursor-pointer">
                  Technical Details (Development Only)
                </summary>
                <pre className="mt-2 text-xs text-gray-600 bg-gray-100 p-3 rounded overflow-auto">
                  {error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      </div>

      {/* Skip Link for Keyboard Navigation */}
      <a
        href="#main-navigation"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-purple-600 text-white px-4 py-2 rounded z-50"
      >
        Skip to main navigation
      </a>

      {/* Screen Reader Status */}
      <div 
        role="status" 
        aria-live="polite" 
        className="sr-only"
      >
        Error page loaded with code {displayCode}
      </div>
    </div>
  )
}

export default ErrorPage