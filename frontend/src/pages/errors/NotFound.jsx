import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getButtonProps, getImageAltText } from '../../utils/accessibility'
import {
  HomeIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'

export default function NotFound() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      {/* Skip Link for Screen Readers */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:z-50"
      >
        Skip to main content
      </a>

      {/* Main Content */}
      <main
        id="main-content"
        className="flex-grow flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8"
        role="main"
        aria-labelledby="error-heading"
      >
        <div className="max-w-md w-full text-center">
          {/* Error Icon with ARIA */}
          <div className="mb-8">
            <div
              className="mx-auto h-24 w-24 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center"
              role="img"
              aria-label="Page not found error"
            >
              <ExclamationTriangleIcon
                className="h-12 w-12 text-red-600 dark:text-red-400"
                aria-hidden="true"
              />
            </div>
          </div>

          {/* Error Message */}
          <div className="mb-8">
            <h1
              id="error-heading"
              className="text-6xl font-bold text-gray-900 dark:text-white mb-4"
            >
              404
            </h1>
            <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Page Not Found
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              The page you are looking for doesn't exist or has been moved.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="space-y-4">
            {/* Primary Action - Go Home */}
            <Link
              to={isAuthenticated ? '/dashboard' : '/'}
              className="w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              aria-label={`Go to ${isAuthenticated ? 'dashboard' : 'home page'}`}
              {...getButtonProps('navigate to home')}
            >
              <HomeIcon className="w-5 h-5 mr-2" aria-hidden="true" />
              {isAuthenticated ? 'Go to Dashboard' : 'Go Home'}
            </Link>

            {/* Secondary Action - Search */}
            {isAuthenticated && (
              <Link
                to="/dashboard"
                className="w-full inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                aria-label="Search for content"
              >
                <MagnifyingGlassIcon
                  className="w-5 h-5 mr-2"
                  aria-hidden="true"
                />
                Search Content
              </Link>
            )}
          </div>

          {/* Help Section */}
          <div className="mt-12 p-6 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Need Help?
            </h3>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <p>If you believe this is an error, please try:</p>
              <ul className="list-disc list-inside space-y-1 mt-2">
                <li>Checking the URL for typos</li>
                <li>Using the navigation menu</li>
                <li>Going back to the previous page</li>
                {isAuthenticated && <li>Searching for your content</li>}
              </ul>
            </div>
          </div>

          {/* Additional Context for Screen Readers */}
          <div className="sr-only">
            <p>
              You have reached a 404 error page. This means the requested page
              could not be found. You can use the navigation buttons above to
              return to the main application or search for content.
            </p>
          </div>
        </div>
      </main>

      {/* Footer with Support Link */}
      <footer className="p-6 text-center border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Still having trouble?{' '}
          <a
            href="mailto:support@lily-ai-socialmedia.com"
            className="text-blue-600 hover:text-blue-500 focus:outline-none focus:underline"
            aria-label="Contact support via email"
          >
            Contact Support
          </a>
        </p>
      </footer>
    </div>
  )
}
