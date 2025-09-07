import React from 'react'
import { usePlan } from '../../contexts/PlanContext'
import { createPlanConditionals, FEATURE_GATES, TIER_REQUIREMENTS, USAGE_LIMITS } from '../../utils/planConditionals'
import { 
  ExclamationTriangleIcon, 
  LockClosedIcon,
  ArrowUpIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline'

/**
 * Enhanced Plan Gate with advanced conditional rendering
 * 
 * Provides comprehensive plan-based access control with:
 * - Feature-based gating
 * - Tier-based gating  
 * - Usage limit gating
 * - Custom fallback components
 * - Upgrade prompts with analytics
 * - Progressive disclosure patterns
 */
const EnhancedPlanGate = ({
  children,
  
  // Access control
  requiredFeature = null,
  requiredTier = null,
  requiredLimit = null,
  limitAction = null,
  
  // UI behavior
  mode = 'hide', // 'hide', 'upgrade', 'disable', 'blur'
  fallback = null,
  showUpgradePrompt = true,
  upgradeStyle = 'banner', // 'banner', 'modal', 'inline', 'toast'
  
  // Accessibility
  ariaLabel = null,
  ariaDescribedBy = null,
  
  // Analytics
  trackingEvent = null,
  
  // Styling
  className = '',
  disabledClassName = 'opacity-50 pointer-events-none',
  blurClassName = 'blur-sm pointer-events-none select-none',
  
  // Progressive disclosure
  showPreview = false,
  previewHeight = '100px',
  
  ...props
}) => {
  const { plan, limits, loading, getUpgradeMessage } = usePlan()
  
  // Create conditionals instance
  const conditionals = React.useMemo(() => {
    return createPlanConditionals(plan, limits)
  }, [plan, limits])

  // Show loading skeleton
  if (loading) {
    return (
      <div className={`animate-pulse ${className}`} aria-label="Loading plan information">
        <div className="bg-gray-200 dark:bg-gray-700 rounded h-4 w-full mb-2"></div>
        <div className="bg-gray-200 dark:bg-gray-700 rounded h-4 w-3/4"></div>
      </div>
    )
  }

  // Check access permissions
  let hasAccess = true
  let accessReason = ''

  // Feature-based access control
  if (requiredFeature) {
    if (!conditionals.hasFeature(requiredFeature)) {
      hasAccess = false
      accessReason = `This feature requires ${requiredFeature.replace('_', ' ')}`
    }
  }

  // Tier-based access control
  if (requiredTier) {
    if (!conditionals.hasPlanTier(requiredTier)) {
      hasAccess = false
      accessReason = `This feature requires ${requiredTier} plan or higher`
    }
  }

  // Usage limit access control
  if (requiredLimit) {
    if (!conditionals.canPerformAction(requiredLimit, limitAction)) {
      hasAccess = false
      const limitType = requiredLimit.replace('_', ' ')
      accessReason = `You've reached your ${limitType} limit`
    }
  }

  // Track gating events for analytics
  React.useEffect(() => {
    if (trackingEvent && !hasAccess) {
      // Analytics tracking would go here
      console.log('Plan gate blocked:', trackingEvent, accessReason)
    }
  }, [hasAccess, trackingEvent, accessReason])

  // Grant access - render children
  if (hasAccess) {
    return (
      <div 
        className={className}
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        {...props}
      >
        {children}
      </div>
    )
  }

  // Handle no access based on mode
  switch (mode) {
    case 'disable':
      return (
        <div 
          className={`${className} ${disabledClassName}`}
          aria-label={ariaLabel || 'Feature disabled due to plan restrictions'}
          aria-describedby={ariaDescribedBy}
          title={accessReason}
          {...props}
        >
          {children}
        </div>
      )
    
    case 'blur':
      return (
        <div className={`relative ${className}`} {...props}>
          <div 
            className={blurClassName}
            aria-hidden="true"
            style={showPreview ? { height: previewHeight, overflow: 'hidden' } : {}}
          >
            {children}
          </div>
          {showUpgradePrompt && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/90 dark:bg-gray-900/90">
              <UpgradePrompt 
                reason={accessReason}
                style="inline"
                conditionals={conditionals}
                requiredFeature={requiredFeature}
                requiredTier={requiredTier}
              />
            </div>
          )}
        </div>
      )
    
    case 'upgrade':
      return showUpgradePrompt ? (
        <UpgradePrompt 
          reason={accessReason}
          style={upgradeStyle}
          className={className}
          conditionals={conditionals}
          requiredFeature={requiredFeature}
          requiredTier={requiredTier}
          {...props}
        />
      ) : (
        fallback || null
      )
    
    case 'hide':
    default:
      return fallback || null
  }
}

/**
 * Upgrade Prompt Component
 */
const UpgradePrompt = ({ 
  reason, 
  style = 'banner', 
  className = '', 
  conditionals,
  requiredFeature,
  requiredTier 
}) => {
  const upgradeMessage = conditionals.getUpgradeMessage(
    requiredFeature || requiredTier || 'this feature'
  )
  
  const handleUpgradeClick = () => {
    // Track upgrade click
    console.log('Upgrade clicked from plan gate')
    window.location.href = '/billing'
  }

  const promptContent = (
    <>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <LockClosedIcon className="h-5 w-5 text-amber-400" aria-hidden="true" />
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
            Upgrade Required
          </h3>
          <div className="mt-1 text-sm text-amber-700 dark:text-amber-300">
            <p>{reason}</p>
            <p className="mt-1">{upgradeMessage}</p>
          </div>
        </div>
        <div className="ml-4 flex-shrink-0">
          <button
            onClick={handleUpgradeClick}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-amber-800 bg-amber-100 hover:bg-amber-200 dark:bg-amber-900 dark:text-amber-200 dark:hover:bg-amber-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
          >
            <ArrowUpIcon className="h-3 w-3 mr-1" aria-hidden="true" />
            Upgrade Now
          </button>
        </div>
      </div>
    </>
  )

  switch (style) {
    case 'banner':
      return (
        <div className={`bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 ${className}`}>
          {promptContent}
        </div>
      )
    
    case 'inline':
      return (
        <div className={`flex flex-col items-center justify-center p-6 text-center ${className}`}>
          <LockClosedIcon className="h-8 w-8 text-amber-500 mb-2" aria-hidden="true" />
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
            Upgrade Required
          </h3>
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
            {upgradeMessage}
          </p>
          <button
            onClick={handleUpgradeClick}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
          >
            <ArrowUpIcon className="h-4 w-4 mr-2" aria-hidden="true" />
            Upgrade Plan
          </button>
        </div>
      )
    
    case 'toast':
      return (
        <div className={`fixed bottom-4 right-4 max-w-md bg-white dark:bg-gray-800 shadow-lg rounded-lg p-4 border border-amber-200 dark:border-amber-800 ${className}`}>
          {promptContent}
        </div>
      )
    
    default:
      return (
        <div className={`bg-amber-50 dark:bg-amber-900/20 rounded-md p-3 ${className}`}>
          {promptContent}
        </div>
      )
  }
}

/**
 * Specific gate components for common use cases
 */
export const FeatureGate = ({ feature, children, ...props }) => (
  <EnhancedPlanGate requiredFeature={feature} {...props}>
    {children}
  </EnhancedPlanGate>
)

export const TierGate = ({ tier, children, ...props }) => (
  <EnhancedPlanGate requiredTier={tier} {...props}>
    {children}
  </EnhancedPlanGate>
)

export const UsageLimitGate = ({ limitType, action, children, ...props }) => (
  <EnhancedPlanGate requiredLimit={limitType} limitAction={action} {...props}>
    {children}
  </EnhancedPlanGate>
)

/**
 * Plan-aware conditional wrapper
 */
export const PlanConditional = ({ when, children, fallback = null }) => {
  const { plan, limits } = usePlan()
  const conditionals = createPlanConditionals(plan, limits)
  
  let shouldShow = true
  
  if (when.feature && !conditionals.hasFeature(when.feature)) {
    shouldShow = false
  }
  
  if (when.tier && !conditionals.hasPlanTier(when.tier)) {
    shouldShow = false
  }
  
  if (when.limit && !conditionals.canPerformAction(when.limit, when.action)) {
    shouldShow = false
  }
  
  return shouldShow ? children : fallback
}

/**
 * Usage indicator with plan awareness
 */
export const EnhancedUsageIndicator = ({
  limitType,
  showUpgradePrompt = true,
  size = 'default',
  orientation = 'horizontal',
  showPercentage = true,
  showRemaining = false,
  className = ''
}) => {
  const { limits } = usePlan()
  const conditionals = createPlanConditionals(null, limits)
  
  if (!limits || !limits[limitType]) return null
  
  const limit = limits[limitType]
  const current = limit.current || 0
  const max = limit.max || 1
  const percentage = conditionals.getUsagePercentage(limitType)
  const remaining = max - current
  
  const isNear = conditionals.isNearLimit(limitType)
  const isAt = conditionals.isAtLimit(limitType)
  
  const sizeClasses = {
    small: 'h-1.5',
    default: 'h-2', 
    large: 'h-3'
  }
  
  const colorClass = isAt ? 'bg-red-500' : isNear ? 'bg-amber-500' : 'bg-emerald-500'
  
  return (
    <div className={`${className}`}>
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-gray-700 dark:text-gray-300 font-medium">
          {limitType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
        </span>
        <div className="flex items-center space-x-2 text-xs">
          {showPercentage && (
            <span className="text-gray-600 dark:text-gray-400">
              {Math.round(percentage)}%
            </span>
          )}
          <span className="text-gray-900 dark:text-gray-100 font-semibold">
            {current} / {max}
          </span>
          {showRemaining && remaining > 0 && (
            <span className="text-emerald-600 dark:text-emerald-400">
              ({remaining} left)
            </span>
          )}
        </div>
      </div>
      
      <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full ${sizeClasses[size]}`}>
        <div
          className={`${sizeClasses[size]} rounded-full transition-all duration-300 ${colorClass}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={`${limitType} usage: ${current} of ${max}`}
        />
      </div>
      
      {(isNear || isAt) && showUpgradePrompt && conditionals.canUpgrade() && (
        <div className={`mt-3 p-3 rounded-lg ${isAt ? 'bg-red-50 border border-red-200 dark:bg-red-900/20 dark:border-red-800' : 'bg-amber-50 border border-amber-200 dark:bg-amber-900/20 dark:border-amber-800'}`}>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className={`text-xs font-medium ${isAt ? 'text-red-800 dark:text-red-200' : 'text-amber-800 dark:text-amber-200'}`}>
                {isAt ? 'Limit Reached' : 'Near Limit'}
              </p>
              <p className={`text-xs ${isAt ? 'text-red-700 dark:text-red-300' : 'text-amber-700 dark:text-amber-300'} mt-1`}>
                {conditionals.getUpgradeMessage(`${limitType} limit`)}
              </p>
            </div>
            <button
              onClick={() => window.location.href = '/billing'}
              className={`ml-3 inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded ${
                isAt 
                  ? 'text-red-700 bg-red-100 hover:bg-red-200 dark:text-red-200 dark:bg-red-900 dark:hover:bg-red-800' 
                  : 'text-amber-700 bg-amber-100 hover:bg-amber-200 dark:text-amber-200 dark:bg-amber-900 dark:hover:bg-amber-800'
              } transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500`}
            >
              <ArrowUpIcon className="h-3 w-3 mr-1" aria-hidden="true" />
              Upgrade
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default EnhancedPlanGate