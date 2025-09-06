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

// Usage limit indicator component
export const UsageLimitIndicator = ({ limitType, className = '' }) => {
  const { limits } = usePlan()

  if (!limits || !limits[limitType]) return null

  const limit = limits[limitType]
  const currentUsage = limit.current || 0
  const maxUsage = limit.max || 1
  const percentage = Math.min((currentUsage / maxUsage) * 100, 100)

  const getColorClass = (percent) => {
    if (percent >= 90) return 'bg-red-500'
    if (percent >= 75) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <div className={`${className}`}>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-gray-600 capitalize">
          {limitType.replace('_', ' ')}
        </span>
        <span className="text-gray-900 font-medium">
          {currentUsage} / {maxUsage}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${getColorClass(percentage)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export default PlanGate
