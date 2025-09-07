import React from 'react'
import { usePlanConditionals } from '../../hooks/usePlanConditionals'
import { 
  LockClosedIcon, 
  StarIcon, 
  ArrowUpIcon,
  SparklesIcon 
} from '@heroicons/react/24/outline'

/**
 * Collection of plan-aware UI components for consistent conditional rendering
 */

/**
 * Plan-aware button that shows different states based on plan restrictions
 */
export const PlanAwareButton = ({
  children,
  requiredFeature = null,
  requiredTier = null,
  requiredLimit = null,
  limitAction = null,
  disableOnRestriction = true,
  showUpgradeHint = true,
  className = '',
  onClick = () => {},
  ...props
}) => {
  const { getButtonState } = usePlanConditionals()
  
  const buttonState = getButtonState({
    requiredFeature,
    requiredTier,
    requiredLimit,
    limitAction,
    disableOnLimit: disableOnRestriction,
    showUpgradeOnRestriction: showUpgradeHint
  })
  
  const baseClasses = disableOnRestriction && buttonState.disabled
    ? 'opacity-50 cursor-not-allowed'
    : 'cursor-pointer'
  
  const handleClick = (e) => {
    if (buttonState.disabled && disableOnRestriction) {
      e.preventDefault()
      if (buttonState.showUpgrade) {
        window.location.href = '/billing'
      }
      return
    }
    onClick(e)
  }
  
  return (
    <div className="relative">
      <button
        className={`${className} ${baseClasses}`}
        onClick={handleClick}
        disabled={buttonState.disabled && disableOnRestriction}
        title={buttonState.disabled ? buttonState.upgradeMessage : ''}
        {...props}
      >
        {children}
        {buttonState.disabled && showUpgradeHint && (
          <LockClosedIcon className="h-3 w-3 ml-1 inline-block" />
        )}
      </button>
      
      {buttonState.showUpgrade && (
        <div className="absolute top-full left-0 mt-1 z-10 w-max max-w-xs bg-amber-50 border border-amber-200 rounded-md p-2 shadow-sm">
          <p className="text-xs text-amber-800">{buttonState.upgradeMessage}</p>
        </div>
      )}
    </div>
  )
}

/**
 * Plan-aware feature indicator/badge
 */
export const PlanFeatureBadge = ({ 
  featureName,
  variant = 'premium', // 'premium', 'pro', 'enterprise'
  size = 'sm',
  showTooltip = true
}) => {
  const { hasFeature } = usePlanConditionals()
  
  if (hasFeature(featureName)) {
    return null // Don't show badge if user has feature
  }
  
  const variants = {
    premium: {
      bg: 'bg-gradient-to-r from-amber-400 to-orange-500',
      text: 'text-white',
      icon: StarIcon,
      label: 'Premium'
    },
    pro: {
      bg: 'bg-gradient-to-r from-purple-500 to-indigo-600',
      text: 'text-white', 
      icon: SparklesIcon,
      label: 'Pro'
    },
    enterprise: {
      bg: 'bg-gradient-to-r from-gray-700 to-black',
      text: 'text-white',
      icon: ArrowUpIcon,
      label: 'Enterprise'
    }
  }
  
  const variantConfig = variants[variant]
  const Icon = variantConfig.icon
  
  const sizes = {
    xs: 'px-1.5 py-0.5 text-xs',
    sm: 'px-2 py-1 text-xs', 
    md: 'px-2.5 py-1.5 text-sm',
    lg: 'px-3 py-2 text-base'
  }
  
  return (
    <span 
      className={`inline-flex items-center rounded-full font-medium ${variantConfig.bg} ${variantConfig.text} ${sizes[size]}`}
      title={showTooltip ? `${variantConfig.label} feature - upgrade to access` : ''}
    >
      <Icon className="h-3 w-3 mr-1" />
      {variantConfig.label}
    </span>
  )
}

/**
 * Plan-aware section wrapper that shows upgrade prompts for sections
 */
export const PlanSection = ({
  children,
  title,
  description,
  requiredFeature = null,
  requiredTier = null,
  mode = 'blur', // 'blur', 'hide', 'disable'
  showUpgradeButton = true,
  className = ''
}) => {
  const { hasFeature, hasPlanTier, getUpgradeMessage } = usePlanConditionals()
  
  let hasAccess = true
  let upgradeMessage = ''
  
  if (requiredFeature && !hasFeature(requiredFeature)) {
    hasAccess = false
    upgradeMessage = getUpgradeMessage(requiredFeature)
  }
  
  if (requiredTier && !hasPlanTier(requiredTier)) {
    hasAccess = false
    upgradeMessage = getUpgradeMessage(requiredTier)
  }
  
  if (hasAccess) {
    return <div className={className}>{children}</div>
  }
  
  switch (mode) {
    case 'hide':
      return null
      
    case 'disable':
      return (
        <div className={`${className} opacity-50 pointer-events-none`}>
          {children}
        </div>
      )
      
    case 'blur':
    default:
      return (
        <div className={`relative ${className}`}>
          <div className="blur-sm pointer-events-none select-none">
            {children}
          </div>
          <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
            <div className="text-center p-6 bg-white rounded-lg shadow-lg border border-gray-200 max-w-sm">
              <LockClosedIcon className="h-8 w-8 text-amber-500 mx-auto mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-sm text-gray-600 mb-4">{description || upgradeMessage}</p>
              {showUpgradeButton && (
                <button
                  onClick={() => window.location.href = '/billing'}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
                >
                  <ArrowUpIcon className="h-4 w-4 mr-2" />
                  Upgrade Now
                </button>
              )}
            </div>
          </div>
        </div>
      )
  }
}

/**
 * Plan-aware navigation item
 */
export const PlanNavItem = ({ 
  children,
  requiredFeature = null,
  requiredTier = null,
  showBadge = true,
  className = ''
}) => {
  const { shouldShowNavItem, hasFeature, hasPlanTier } = usePlanConditionals()
  
  const shouldShow = shouldShowNavItem({ requiredFeature, requiredTier })
  
  if (!shouldShow) {
    return null
  }
  
  const needsBadge = showBadge && (
    (requiredFeature && !hasFeature(requiredFeature)) ||
    (requiredTier && !hasPlanTier(requiredTier))
  )
  
  return (
    <div className={`flex items-center ${className}`}>
      {children}
      {needsBadge && (
        <PlanFeatureBadge 
          featureName={requiredFeature || requiredTier}
          variant={requiredTier === 'enterprise' ? 'enterprise' : requiredTier === 'pro' ? 'pro' : 'premium'}
          size="xs"
        />
      )}
    </div>
  )
}

/**
 * Plan-aware content preview (shows snippet with upgrade prompt)
 */
export const PlanContentPreview = ({
  children,
  requiredFeature = null,
  requiredTier = null,
  previewHeight = '100px',
  upgradeTitle = 'Premium Content',
  upgradeDescription = 'Upgrade to view full content',
  className = ''
}) => {
  const { hasFeature, hasPlanTier, getUpgradeMessage } = usePlanConditionals()
  
  let hasAccess = true
  
  if (requiredFeature && !hasFeature(requiredFeature)) {
    hasAccess = false
  }
  
  if (requiredTier && !hasPlanTier(requiredTier)) {
    hasAccess = false
  }
  
  if (hasAccess) {
    return <div className={className}>{children}</div>
  }
  
  return (
    <div className={`relative ${className}`}>
      <div 
        className="overflow-hidden"
        style={{ height: previewHeight }}
      >
        <div className="blur-sm pointer-events-none select-none">
          {children}
        </div>
      </div>
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white/90 to-transparent p-4 text-center">
        <h4 className="font-medium text-gray-900 mb-1">{upgradeTitle}</h4>
        <p className="text-sm text-gray-600 mb-3">{upgradeDescription}</p>
        <button
          onClick={() => window.location.href = '/billing'}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-amber-700 bg-amber-100 rounded-md hover:bg-amber-200 transition-colors"
        >
          <ArrowUpIcon className="h-3 w-3 mr-1" />
          Unlock Content
        </button>
      </div>
    </div>
  )
}

/**
 * Plan-aware tooltip that shows upgrade information
 */
export const PlanTooltip = ({
  children,
  requiredFeature = null,
  requiredTier = null,
  placement = 'top'
}) => {
  const { hasFeature, hasPlanTier, getUpgradeMessage } = usePlanConditionals()
  
  let hasAccess = true
  let upgradeMessage = ''
  
  if (requiredFeature && !hasFeature(requiredFeature)) {
    hasAccess = false
    upgradeMessage = getUpgradeMessage(requiredFeature)
  }
  
  if (requiredTier && !hasPlanTier(requiredTier)) {
    hasAccess = false
    upgradeMessage = getUpgradeMessage(requiredTier)
  }
  
  if (hasAccess) {
    return children
  }
  
  return (
    <div className="relative group">
      {children}
      <div className={`absolute z-10 invisible group-hover:visible bg-gray-900 text-white text-xs rounded py-1 px-2 ${
        placement === 'top' ? 'bottom-full mb-1' : 'top-full mt-1'
      } left-1/2 transform -translate-x-1/2 whitespace-nowrap`}>
        {upgradeMessage}
        <div className={`absolute left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45 ${
          placement === 'top' ? 'top-full -mt-1' : 'bottom-full -mb-1'
        }`}></div>
      </div>
    </div>
  )
}

/**
 * Plan-aware form field wrapper
 */
export const PlanFormField = ({
  children,
  requiredFeature = null,
  requiredTier = null,
  showUpgradeHint = true,
  className = ''
}) => {
  const { hasFeature, hasPlanTier, getUpgradeMessage } = usePlanConditionals()
  
  let hasAccess = true
  let upgradeMessage = ''
  
  if (requiredFeature && !hasFeature(requiredFeature)) {
    hasAccess = false
    upgradeMessage = getUpgradeMessage(requiredFeature)
  }
  
  if (requiredTier && !hasPlanTier(requiredTier)) {
    hasAccess = false
    upgradeMessage = getUpgradeMessage(requiredTier)
  }
  
  if (hasAccess) {
    return <div className={className}>{children}</div>
  }
  
  return (
    <div className={`relative ${className}`}>
      <div className="opacity-50 pointer-events-none">
        {children}
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="bg-amber-100 border border-amber-300 rounded-md px-2 py-1">
          <div className="flex items-center text-xs text-amber-800">
            <LockClosedIcon className="h-3 w-3 mr-1" />
            Premium Feature
          </div>
        </div>
      </div>
      {showUpgradeHint && (
        <p className="text-xs text-amber-600 mt-1">{upgradeMessage}</p>
      )}
    </div>
  )
}

export default {
  PlanAwareButton,
  PlanFeatureBadge,
  PlanSection,
  PlanNavItem,
  PlanContentPreview,
  PlanTooltip,
  PlanFormField
}