import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  ExclamationTriangleIcon, 
  HomeIcon, 
  ChevronLeftIcon 
} from '@heroicons/react/24/outline'

/**
 * WCAG 2.1 AA Compliant 404 Not Found Page
 * 
 * Accessibility Features:
 * - Proper heading hierarchy (h1 -> h2 -> h3)
 * - High contrast colors (4.5:1 minimum)
 * - Focus management and keyboard navigation
 * - Screen reader friendly content
 * - Clear error messaging and recovery options
 * - Semantic HTML structure
 */
const NotFound = () => {
  // Announce to screen readers when page loads
  useEffect(() => {
    document.title = 'Page Not Found - Lily AI Social Media'
    
    // Announce error to screen readers
    const announcement = document.createElement('div')
    announcement.setAttribute('aria-live', 'polite')
    announcement.setAttribute('aria-atomic', 'true')
    announcement.className = 'sr-only'
    announcement.textContent = 'Error 404: The page you requested could not be found'
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
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* Error Icon */}
          <div className="flex justify-center mb-6">
            <div 
              className="rounded-full bg-red-100 p-3"
              role="img"
              aria-label="Error indicator"
            >
              <ExclamationTriangleIcon 
                className="h-8 w-8 text-red-600" 
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
              404 - Page Not Found
            </h1>
            
            <h2 className="text-lg text-gray-700 mb-6">
              We couldn't find what you're looking for
            </h2>

            <div className="space-y-4 mb-8 text-left">
              <p className="text-sm text-gray-600">
                The page you're looking for might have been:
              </p>
              <ul 
                className="text-sm text-gray-600 space-y-2"
                role="list"
              >
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>Moved to a different location</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>Temporarily unavailable</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>Removed or deleted</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>Entered incorrectly in the address bar</span>
                </li>
              </ul>
            </div>

            {/* Recovery Actions */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                What you can do:
              </h3>
              
              <div className="space-y-3">
                <Link
                  to="/"
                  className="w-full flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
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

            {/* Help Section */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Need Help?
              </h3>
              <p className="text-xs text-gray-600 mb-3">
                If you believe this is an error, please contact our support team.
              </p>
              <Link
                to="/settings"
                className="text-sm text-purple-600 hover:text-purple-500 underline focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 rounded"
              >
                Contact Support
              </Link>
            </div>
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
    </div>
  )
}

export default NotFound