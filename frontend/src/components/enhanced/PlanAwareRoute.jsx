import React from 'react'
import { Navigate } from 'react-router-dom'
import { usePlan } from '../../contexts/PlanContext'
import { createPlanConditionals } from '../../utils/planConditionals'
import { 
  LockClosedIcon, 
  ArrowUpIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline'

/**
 * Plan-aware routing component that restricts access to routes based on plan features
 */
const PlanAwareRoute = ({ 
  children,
  
  // Access requirements
  requiredFeature = null,
  requiredTier = null,
  requiredLimit = null,
  limitAction = null,
  
  // Fallback behavior
  fallbackMode = 'billing', // 'billing', '403', 'upgrade-page', 'navigate'
  fallbackPath = '/403',
  
  // Upgrade page customization
  upgradeTitle = 'Upgrade Required',
  upgradeDescription = null,
  
  // Loading state
  loadingComponent = null,
  
  className = ''
}) => {
  const { plan, limits, loading } = usePlan()
  
  // Show loading state
  if (loading) {
    if (loadingComponent) {
      return loadingComponent
    }
    
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading plan information...</p>
        </div>
      </div>
    )
  }
  
  const conditionals = createPlanConditionals(plan, limits)
  
  // Check access permissions
  let hasAccess = true
  let accessReason = ''
  
  if (requiredFeature && !conditionals.hasFeature(requiredFeature)) {
    hasAccess = false
    accessReason = `This page requires ${requiredFeature.replace('_', ' ')}`
  }
  
  if (requiredTier && !conditionals.hasPlanTier(requiredTier)) {
    hasAccess = false
    accessReason = `This page requires ${requiredTier} plan or higher`
  }
  
  if (requiredLimit && !conditionals.canPerformAction(requiredLimit, limitAction)) {
    hasAccess = false
    const limitType = requiredLimit.replace('_', ' ')
    accessReason = `You've reached your ${limitType} limit`
  }
  
  // Grant access
  if (hasAccess) {
    return <div className={className}>{children}</div>
  }
  
  // Handle access denial based on fallback mode
  switch (fallbackMode) {
    case 'billing':
      return <Navigate to="/billing" replace />
      
    case '403':
      return <Navigate to="/403" replace />
      
    case 'navigate':
      return <Navigate to={fallbackPath} replace />
      
    case 'upgrade-page':
    default:
      return (
        <UpgradeRequiredPage
          reason={accessReason}
          title={upgradeTitle}
          description={upgradeDescription || conditionals.getUpgradeMessage('this page')}
          conditionals={conditionals}
          requiredFeature={requiredFeature}
          requiredTier={requiredTier}
        />
      )
  }
}

/**
 * Upgrade Required Page Component
 */
const UpgradeRequiredPage = ({ 
  reason, 
  title, 
  description, 
  conditionals,
  requiredFeature,
  requiredTier 
}) => {
  const handleUpgradeClick = () => {
    window.location.href = '/billing'
  }
  
  const handleGoBack = () => {
    window.history.back()
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="text-center">
          {/* Icon */}
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-amber-100 dark:bg-amber-900/20 mb-6">
            <LockClosedIcon className="h-8 w-8 text-amber-600 dark:text-amber-400" aria-hidden="true" />
          </div>
          
          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            {title}
          </h1>
          
          {/* Reason */}
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {reason}
          </p>
          
          {/* Description */}
          <p className="text-sm text-gray-500 dark:text-gray-500 mb-8">
            {description}
          </p>
          
          {/* Action buttons */}
          <div className="space-y-3">
            <button
              onClick={handleUpgradeClick}
              className="w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
            >
              <ArrowUpIcon className="h-5 w-5 mr-2" aria-hidden="true" />
              Upgrade Plan
            </button>
            
            <button
              onClick={handleGoBack}
              className="w-full flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
            >
              Go Back
            </button>
          </div>
        </div>
        
        {/* Plan comparison hint */}
        {conditionals.canUpgrade() && (
          <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-blue-400 mr-2" aria-hidden="true" />
              <p className="text-sm text-blue-800 dark:text-blue-200">
                View our <a href="/billing" className="underline hover:no-underline">pricing plans</a> to find the right fit for your needs.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Higher-order component for plan-aware routes
 */
export const withPlanRoute = (Component, routeConfig = {}) => {
  return function PlanProtectedComponent(props) {
    return (
      <PlanAwareRoute {...routeConfig}>
        <Component {...props} />
      </PlanAwareRoute>
    )
  }
}

/**
 * Common route configurations
 */
export const ROUTE_CONFIGS = {
  // Feature-based routes
  AI_INBOX: {
    requiredFeature: 'ai_inbox',
    upgradeTitle: 'AI Inbox - Premium Feature',
    upgradeDescription: 'Manage all your social media messages with AI-powered assistance'
  },
  
  PREMIUM_AI: {
    requiredFeature: 'premium_ai_models',
    upgradeTitle: 'Premium AI - Advanced Content',
    upgradeDescription: 'Access GPT-4 and advanced AI models for superior content creation'
  },
  
  ENHANCED_AUTOPILOT: {
    requiredFeature: 'enhanced_autopilot',
    upgradeTitle: 'Enhanced Autopilot - Full Automation',
    upgradeDescription: 'Let AI handle your entire content strategy automatically'
  },
  
  ADVANCED_ANALYTICS: {
    requiredFeature: 'advanced_analytics',
    upgradeTitle: 'Advanced Analytics - Deep Insights',
    upgradeDescription: 'Get detailed performance metrics and audience insights'
  },
  
  // Tier-based routes  
  PRO_FEATURES: {
    requiredTier: 'pro',
    upgradeTitle: 'Pro Features Required',
    upgradeDescription: 'This feature is available with Pro and Enterprise plans'
  },
  
  ENTERPRISE_FEATURES: {
    requiredTier: 'enterprise',
    upgradeTitle: 'Enterprise Features Required', 
    upgradeDescription: 'This feature is available only with Enterprise plans'
  }
}

/**
 * Convenience components for common routes
 */
export const AIInboxRoute = ({ children }) => (
  <PlanAwareRoute {...ROUTE_CONFIGS.AI_INBOX}>
    {children}
  </PlanAwareRoute>
)

export const PremiumAIRoute = ({ children }) => (
  <PlanAwareRoute {...ROUTE_CONFIGS.PREMIUM_AI}>
    {children}
  </PlanAwareRoute>
)

export const EnhancedAutopilotRoute = ({ children }) => (
  <PlanAwareRoute {...ROUTE_CONFIGS.ENHANCED_AUTOPILOT}>
    {children}
  </PlanAwareRoute>
)

export const AdvancedAnalyticsRoute = ({ children }) => (
  <PlanAwareRoute {...ROUTE_CONFIGS.ADVANCED_ANALYTICS}>
    {children}
  </PlanAwareRoute>
)

export const ProRoute = ({ children }) => (
  <PlanAwareRoute {...ROUTE_CONFIGS.PRO_FEATURES}>
    {children}
  </PlanAwareRoute>
)

export const EnterpriseRoute = ({ children }) => (
  <PlanAwareRoute {...ROUTE_CONFIGS.ENTERPRISE_FEATURES}>
    {children}
  </PlanAwareRoute>
)

export default PlanAwareRoute