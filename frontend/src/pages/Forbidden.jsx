import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  ShieldExclamationIcon, 
  HomeIcon, 
  ChevronLeftIcon,
  ArrowRightOnRectangleIcon 
} from '@heroicons/react/24/outline'

/**
 * WCAG 2.1 AA Compliant 403 Forbidden Page
 * 
 * Accessibility Features:
 * - Proper heading hierarchy (h1 -> h2 -> h3)
 * - High contrast colors (4.5:1 minimum)
 * - Focus management and keyboard navigation
 * - Screen reader friendly content
 * - Clear error messaging and recovery options
 * - Semantic HTML structure with roles
 */
const Forbidden = () => {
  // Announce to screen readers when page loads
  useEffect(() => {
    document.title = 'Access Forbidden - Lily AI Social Media'
    
    // Announce error to screen readers
    const announcement = document.createElement('div')
    announcement.setAttribute('aria-live', 'assertive')
    announcement.setAttribute('aria-atomic', 'true')
    announcement.className = 'sr-only'
    announcement.textContent = 'Error 403: Access to this resource is forbidden. You do not have the necessary permissions.'
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
              aria-label="Access denied indicator"
            >
              <ShieldExclamationIcon 
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
              403 - Access Forbidden
            </h1>
            
            <h2 className="text-lg text-gray-700 mb-6">
              You don't have permission to access this resource
            </h2>

            <div className="space-y-4 mb-8 text-left">
              <p className="text-sm text-gray-600">
                This might happen because:
              </p>
              <ul 
                className="text-sm text-gray-600 space-y-2"
                role="list"
              >
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>Your session has expired</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>You don't have the required subscription plan</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>Your account permissions have been updated</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2" aria-hidden="true">•</span>
                  <span>This feature is restricted to certain user roles</span>
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
                  Return to Dashboard
                </Link>

                <Link
                  to="/login"
                  className="w-full flex justify-center items-center px-4 py-2 border border-purple-300 rounded-md shadow-sm bg-white text-sm font-medium text-purple-700 hover:bg-purple-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
                >
                  <ArrowRightOnRectangleIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                  Sign In Again
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

            {/* Plan Upgrade Section */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Need Access?
              </h3>
              <p className="text-xs text-gray-600 mb-3">
                This feature might be available with a higher subscription plan.
              </p>
              <div className="flex flex-col sm:flex-row gap-2">
                <Link
                  to="/billing"
                  className="flex-1 text-center px-3 py-2 text-sm text-purple-600 hover:text-purple-500 underline focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 rounded"
                >
                  View Plans
                </Link>
                <Link
                  to="/settings"
                  className="flex-1 text-center px-3 py-2 text-sm text-purple-600 hover:text-purple-500 underline focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 rounded"
                >
                  Contact Support
                </Link>
              </div>
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

      {/* Screen Reader Status */}
      <div 
        role="status" 
        aria-live="polite" 
        className="sr-only"
      >
        Page loaded: Access denied error page
      </div>
    </div>
  )
}

export default Forbidden