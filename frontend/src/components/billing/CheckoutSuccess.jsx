import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { usePlan } from '../../contexts/PlanContext'
import { useNotifications } from '../../hooks/useNotifications'
import {
  CheckCircleIcon,
  ArrowRightIcon,
  CreditCardIcon,
  ChartBarIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'

/**
 * Checkout Success Component
 * 
 * Displayed after successful Stripe checkout completion
 * with plan activation confirmation and next steps
 */
const CheckoutSuccess = ({ planName, sessionId }) => {
  const { plan, refreshPlan } = usePlan()
  const { showSuccess } = useNotifications()
  
  useEffect(() => {
    // Refresh plan data to reflect new subscription
    refreshPlan()
    
    // Track successful conversion
    if (window.gtag) {
      window.gtag('event', 'subscription_success', {
        event_category: 'billing',
        event_label: planName,
        value: 1
      })
    }
    
    // Show success notification
    showSuccess(`Welcome to ${planName}! Your subscription is now active.`)
  }, [planName, refreshPlan, showSuccess])
  
  const getNextSteps = (planName) => {
    const baseSteps = [
      {
        title: 'Connect Your Social Accounts',
        description: 'Link your social media profiles to start posting',
        href: '/integrations',
        icon: SparklesIcon
      },
      {
        title: 'Create Your First Post',
        description: 'Use our AI-powered tools to create engaging content',
        href: '/create-post',
        icon: ChartBarIcon
      },
      {
        title: 'Explore Analytics',
        description: 'Track your performance with detailed insights',
        href: '/dashboard',
        icon: ChartBarIcon
      }
    ]
    
    // Add plan-specific next steps
    switch (planName?.toLowerCase()) {
      case 'pro':
      case 'enterprise':
        return [
          {
            title: 'Set Up AI Inbox',
            description: 'Manage all your social messages with AI assistance',
            href: '/inbox',
            icon: SparklesIcon
          },
          ...baseSteps,
          {
            title: 'Configure Brand Vault',
            description: 'Upload your brand assets and style guidelines',
            href: '/memory',
            icon: CreditCardIcon
          }
        ]
      default:
        return baseSteps
    }
  }
  
  const nextSteps = getNextSteps(planName)
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Success Icon */}
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-green-100 dark:bg-green-900">
            <CheckCircleIcon className="h-10 w-10 text-green-600 dark:text-green-400" />
          </div>
          
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900 dark:text-white">
            Welcome to {planName}!
          </h2>
          
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            Your subscription has been activated successfully
          </p>
        </div>
        
        {/* Subscription Details */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Subscription Details
          </h3>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Plan</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {planName} Plan
              </span>
            </div>
            
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Status</span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <CheckCircleIcon className="h-3 w-3 mr-1" />
                Active
              </span>
            </div>
            
            {sessionId && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Session ID</span>
                <span className="text-sm font-mono text-gray-500 dark:text-gray-400">
                  {sessionId.substring(0, 20)}...
                </span>
              </div>
            )}
          </div>
        </div>
        
        {/* P1-10b: Renewal Terms Disclosure */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-4 flex items-center">
            <InformationCircleIcon className="h-5 w-5 mr-2" />
            Important: Renewal Information
          </h3>
          
          <div className="space-y-3 text-sm text-blue-800 dark:text-blue-200">
            <div className="flex items-start space-x-2">
              <CheckCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Automatic Renewal:</strong> Your {planName} subscription will automatically renew each billing cycle
              </span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Easy Cancellation:</strong> Cancel anytime through your billing settings - no fees or penalties
              </span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Notification:</strong> You'll receive email reminders before each renewal
              </span>
            </div>
            <div className="flex items-start space-x-2">
              <CheckCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Control:</strong> Update payment methods, change plans, or cancel through your account at any time
              </span>
            </div>
          </div>
        </div>
        
        {/* Next Steps */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Get Started
          </h3>
          
          <div className="space-y-4">
            {nextSteps.slice(0, 3).map((step, index) => {
              const Icon = step.icon
              return (
                <Link
                  key={index}
                  to={step.href}
                  className="block p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors group"
                >
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        {step.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {step.description}
                      </p>
                    </div>
                    <div className="ml-3">
                      <ArrowRightIcon className="h-4 w-4 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex flex-col space-y-3">
          <Link
            to="/dashboard"
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Go to Dashboard
          </Link>
          
          <Link
            to="/billing"
            className="w-full flex justify-center py-3 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Manage Billing
          </Link>
        </div>
        
        {/* Support */}
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Questions about your subscription?{' '}
            <a
              href="/support"
              className="text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
            >
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default CheckoutSuccess