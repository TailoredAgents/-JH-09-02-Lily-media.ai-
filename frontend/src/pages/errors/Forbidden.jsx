import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { usePlan } from '../../contexts/PlanContext'
import { getButtonProps } from '../../utils/accessibility'
import {
  ShieldExclamationIcon,
  HomeIcon,
  CreditCardIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'

export default function Forbidden() {
  const { isAuthenticated, logout } = useAuth()
  const { plan } = usePlan()

  const handleLogout = () => {
    logout()
  }

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
              aria-label="Access forbidden error"
            >
              <ShieldExclamationIcon
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
              403
            </h1>
            <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Access Forbidden
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              You don't have permission to access this resource. This might be
              due to:
            </p>

            {/* Reason List */}
            <div className="text-left bg-gray-100 dark:bg-gray-800 rounded-lg p-4 mb-6">
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
                <li className="flex items-start">
                  <span className="text-red-500 mr-2">•</span>
                  Insufficient permissions for your current plan
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2">•</span>
                  Session expired or authentication required
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2">•</span>
                  Account restrictions or billing issues
                </li>
                <li className="flex items-start">
                  <span className="text-red-500 mr-2">•</span>
                  Feature not available in your subscription tier
                </li>
              </ul>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-4">
            {isAuthenticated ? (
              <>
                {/* Primary Action - Dashboard */}
                <Link
                  to="/dashboard"
                  className="w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  aria-label="Return to dashboard"
                  {...getButtonProps('navigate to dashboard')}
                >
                  <HomeIcon className="w-5 h-5 mr-2" aria-hidden="true" />
                  Back to Dashboard
                </Link>

                {/* Secondary Action - Billing */}
                {plan && (
                  <Link
                    to="/billing"
                    className="w-full inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                    aria-label="Check billing and upgrade plan"
                  >
                    <CreditCardIcon
                      className="w-5 h-5 mr-2"
                      aria-hidden="true"
                    />
                    Check Billing & Upgrade
                  </Link>
                )}

                {/* Logout Option */}
                <button
                  onClick={handleLogout}
                  className="w-full inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  aria-label="Sign out of your account"
                  {...getButtonProps('logout')}
                >
                  <ArrowRightOnRectangleIcon
                    className="w-5 h-5 mr-2"
                    aria-hidden="true"
                  />
                  Sign Out & Try Different Account
                </button>
              </>
            ) : (
              <>
                {/* Login Action */}
                <Link
                  to="/auth/login"
                  className="w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  aria-label="Sign in to your account"
                  {...getButtonProps('navigate to login')}
                >
                  Sign In
                </Link>

                {/* Home Action */}
                <Link
                  to="/"
                  className="w-full inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  aria-label="Go to home page"
                >
                  <HomeIcon className="w-5 h-5 mr-2" aria-hidden="true" />
                  Go Home
                </Link>
              </>
            )}
          </div>

          {/* Current Plan Info for Authenticated Users */}
          {isAuthenticated && plan && (
            <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900 rounded-lg">
              <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                Current Plan
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-200">
                You're currently on the{' '}
                <strong>{plan.display_name || plan.plan_name}</strong> plan.
                Some features may require an upgrade.
              </p>
            </div>
          )}

          {/* Help Section */}
          <div className="mt-8 p-6 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Need Help?
            </h3>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <p>If you believe you should have access:</p>
              <ul className="list-disc list-inside space-y-1 mt-2">
                <li>Check your account permissions</li>
                <li>Verify your subscription status</li>
                <li>Try refreshing your session</li>
                <li>Contact support if the issue persists</li>
              </ul>
            </div>
          </div>

          {/* Additional Context for Screen Readers */}
          <div className="sr-only">
            <p>
              You have reached a 403 Forbidden error page. This means you don't
              have permission to access this resource. This could be due to
              insufficient permissions, an expired session, or subscription
              limitations. Use the navigation buttons above to return to an
              accessible area or upgrade your plan.
            </p>
          </div>
        </div>
      </main>

      {/* Footer with Support Link */}
      <footer className="p-6 text-center border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Need assistance with access permissions?{' '}
          <a
            href="mailto:support@lily-ai-socialmedia.com"
            className="text-blue-600 hover:text-blue-500 focus:outline-none focus:underline"
            aria-label="Contact support via email for access issues"
          >
            Contact Support
          </a>
        </p>
      </footer>
    </div>
  )
}
