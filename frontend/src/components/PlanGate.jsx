import React from 'react'
import { usePlan } from '../contexts/PlanContext'

const PlanGate = ({
  children,
  feature = null,
  plan = null,
  limit = null,
  limitAction = null,
  fallback = null,
  showUpgradePrompt = false,
  className = '',
}) => {
  const {
    checkFeature,
    isPlanTier,
    checkLimit,
    getUpgradeMessage,
    loading,
    plan: currentPlan,
  } = usePlan()

  // Show loading state if plan data is still loading
  if (loading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="bg-gray-200 rounded h-4 w-24"></div>
      </div>
    )
  }

  // Check access based on different criteria
  let hasAccess = true

  // Check specific feature requirement
  if (feature && !checkFeature(feature)) {
    hasAccess = false
  }

  // Check plan tier requirement
  if (plan && !isPlanTier(plan)) {
    hasAccess = false
  }

  // Check usage limit requirement
  if (limit && !checkLimit(limit, limitAction)) {
    hasAccess = false
  }

  // If user has access, render children
  if (hasAccess) {
    return <div className={className}>{children}</div>
  }

  // If no access and showing upgrade prompt
  if (showUpgradePrompt) {
    const upgradeMessage = getUpgradeMessage(feature || plan || limit)

    return (
      <div
        className={`bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 ${className}`}
      >
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-blue-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm text-blue-800">{upgradeMessage}</p>
          </div>
          <div className="ml-4">
            <button
              onClick={() => (window.location.href = '/billing')}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors"
            >
              Upgrade Now
            </button>
          </div>
        </div>
      </div>
    )
  }

  // If fallback provided, render it
  if (fallback) {
    return <div className={className}>{fallback}</div>
  }

  // Otherwise, render nothing
  return null
}

// Higher-order component for plan-based routing protection
export const withPlanGate = (Component, gateProps = {}) => {
  return function PlanGatedComponent(props) {
    return (
      <PlanGate {...gateProps}>
        <Component {...props} />
      </PlanGate>
    )
  }
}

// Specific gate components for common use cases
export const FeatureGate = ({ feature, children, ...props }) => (
  <PlanGate feature={feature} {...props}>
    {children}
  </PlanGate>
)

export const PlanTierGate = ({ tier, children, ...props }) => (
  <PlanGate plan={tier} {...props}>
    {children}
  </PlanGate>
)

export const UsageGate = ({ limitType, action, children, ...props }) => (
  <PlanGate limit={limitType} limitAction={action} {...props}>
    {children}
  </PlanGate>
)

// Enhanced usage limit indicator component with upgrade prompts
export const UsageLimitIndicator = ({
  limitType,
  className = '',
  showUpgradePrompt = true,
  size = 'default',
}) => {
  const { limits, getUpgradeMessage, canUpgrade } = usePlan()

  if (!limits || !limits[limitType]) return null

  const limit = limits[limitType]
  const currentUsage = limit.current || 0
  const maxUsage = limit.max || 1
  const percentage = Math.min((currentUsage / maxUsage) * 100, 100)
  const isNearLimit = percentage >= 75
  const isAtLimit = percentage >= 90

  const getColorClass = (percent) => {
    if (percent >= 90) return 'bg-red-500'
    if (percent >= 75) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getTextColorClass = (percent) => {
    if (percent >= 90) return 'text-red-700'
    if (percent >= 75) return 'text-yellow-700'
    return 'text-green-700'
  }

  const getLimitLabel = (type) => {
    const labels = {
      posts: 'Posts',
      images: 'Images',
      social_profiles: 'Social Profiles',
      team: 'Team Members',
      workspaces: 'Workspaces',
    }
    return labels[type] || type.replace('_', ' ')
  }

  const sizeClasses = {
    small: { bar: 'h-1.5', text: 'text-xs' },
    default: { bar: 'h-2', text: 'text-sm' },
    large: { bar: 'h-3', text: 'text-base' },
  }

  const { bar: barHeight, text: textSize } = sizeClasses[size]

  return (
    <div className={`${className}`}>
      <div className={`flex items-center justify-between ${textSize} mb-1`}>
        <span className="text-gray-600 dark:text-gray-400 font-medium">
          {getLimitLabel(limitType)}
        </span>
        <span className={`font-semibold ${getTextColorClass(percentage)}`}>
          {currentUsage} / {maxUsage}
        </span>
      </div>

      <div
        className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full ${barHeight} mb-2`}
      >
        <div
          className={`${barHeight} rounded-full transition-all duration-300 ${getColorClass(percentage)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Usage status and upgrade prompt */}
      {(isNearLimit || isAtLimit) && showUpgradePrompt && canUpgrade() && (
        <div
          className={`${isAtLimit ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'} rounded-md p-3 mt-2`}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p
                className={`${textSize} font-medium ${isAtLimit ? 'text-red-800' : 'text-yellow-800'}`}
              >
                {isAtLimit ? 'Limit Reached' : 'Near Limit'}
              </p>
              <p
                className={`text-xs ${isAtLimit ? 'text-red-700' : 'text-yellow-700'} mt-1`}
              >
                {getUpgradeMessage(`${limitType} limit`)}
              </p>
            </div>
            <button
              onClick={() => (window.location.href = '/billing')}
              className={`ml-3 inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded ${
                isAtLimit
                  ? 'text-red-700 bg-red-100 hover:bg-red-200'
                  : 'text-yellow-700 bg-yellow-100 hover:bg-yellow-200'
              } transition-colors`}
            >
              Upgrade
            </button>
          </div>
        </div>
      )}

      {/* Helpful tip for good usage */}
      {!isNearLimit && percentage > 0 && (
        <p className="text-xs text-green-600 mt-1">
          You're using {Math.round(percentage)}% of your{' '}
          {getLimitLabel(limitType).toLowerCase()} limit
        </p>
      )}
    </div>
  )
}

export default PlanGate
