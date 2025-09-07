import { useMemo, useCallback } from 'react'
import { usePlan } from '../contexts/PlanContext'
import { createPlanConditionals, FEATURE_GATES, TIER_REQUIREMENTS, USAGE_LIMITS } from '../utils/planConditionals'

/**
 * Enhanced hook for plan-based conditional logic
 * 
 * Provides comprehensive utilities for plan-aware UI behavior,
 * including feature gating, usage limits, and upgrade prompts.
 */
export const usePlanConditionals = () => {
  const planContext = usePlan()
  const { plan, limits, loading, error } = planContext
  
  // Create conditionals instance
  const conditionals = useMemo(() => {
    return createPlanConditionals(plan, limits)
  }, [plan, limits])
  
  // Feature checking utilities
  const hasFeature = useCallback((featureName) => {
    return conditionals.hasFeature(featureName)
  }, [conditionals])
  
  const hasPlanTier = useCallback((tierName) => {
    return conditionals.hasPlanTier(tierName)
  }, [conditionals])
  
  const canPerformAction = useCallback((limitType, action = 'default') => {
    return conditionals.canPerformAction(limitType, action)
  }, [conditionals])
  
  // Usage monitoring utilities
  const getUsagePercentage = useCallback((limitType) => {
    return conditionals.getUsagePercentage(limitType)
  }, [conditionals])
  
  const isNearLimit = useCallback((limitType) => {
    return conditionals.isNearLimit(limitType)
  }, [conditionals])
  
  const isAtLimit = useCallback((limitType) => {
    return conditionals.isAtLimit(limitType)
  }, [conditionals])
  
  // Upgrade utilities
  const getUpgradeMessage = useCallback((feature) => {
    return conditionals.getUpgradeMessage(feature)
  }, [conditionals])
  
  const canUpgrade = useCallback(() => {
    return conditionals.canUpgrade()
  }, [conditionals])
  
  // Navigation utilities
  const shouldShowNavItem = useCallback((itemConfig) => {
    if (itemConfig.requiredFeature && !hasFeature(itemConfig.requiredFeature)) {
      return false
    }
    
    if (itemConfig.requiredTier && !hasPlanTier(itemConfig.requiredTier)) {
      return false
    }
    
    if (itemConfig.requiredLimit && !canPerformAction(itemConfig.requiredLimit, itemConfig.limitAction)) {
      return false
    }
    
    return true
  }, [hasFeature, hasPlanTier, canPerformAction])
  
  // Button state utilities
  const getButtonState = useCallback((config = {}) => {
    const { 
      requiredFeature,
      requiredTier, 
      requiredLimit,
      limitAction,
      disableOnLimit = true,
      showUpgradeOnRestriction = true
    } = config
    
    let isEnabled = true
    let reason = ''
    
    if (requiredFeature && !hasFeature(requiredFeature)) {
      isEnabled = false
      reason = `Requires ${requiredFeature.replace('_', ' ')}`
    }
    
    if (requiredTier && !hasPlanTier(requiredTier)) {
      isEnabled = false
      reason = `Requires ${requiredTier} plan`
    }
    
    if (requiredLimit && !canPerformAction(requiredLimit, limitAction)) {
      isEnabled = disableOnLimit ? false : true
      reason = `${requiredLimit.replace('_', ' ')} limit reached`
    }
    
    return {
      enabled: isEnabled,
      disabled: !isEnabled,
      reason,
      showUpgrade: !isEnabled && showUpgradeOnRestriction && canUpgrade(),
      upgradeMessage: !isEnabled ? getUpgradeMessage(requiredFeature || requiredTier || requiredLimit) : ''
    }
  }, [hasFeature, hasPlanTier, canPerformAction, canUpgrade, getUpgradeMessage])
  
  // Batch feature checking
  const checkMultipleFeatures = useCallback((features) => {
    return features.reduce((acc, feature) => {
      acc[feature] = hasFeature(feature)
      return acc
    }, {})
  }, [hasFeature])
  
  // Plan-aware styling utilities
  const getPlanAwareStyles = useCallback((config) => {
    const {
      enabledStyles = '',
      disabledStyles = 'opacity-50 cursor-not-allowed',
      nearLimitStyles = 'border-amber-300 bg-amber-50',
      atLimitStyles = 'border-red-300 bg-red-50',
      limitType = null
    } = config
    
    if (limitType) {
      if (isAtLimit(limitType)) return atLimitStyles
      if (isNearLimit(limitType)) return nearLimitStyles
    }
    
    return enabledStyles
  }, [isNearLimit, isAtLimit])
  
  // Usage limit status
  const getLimitStatus = useCallback((limitType) => {
    if (!limits || !limits[limitType]) {
      return {
        status: 'unknown',
        current: 0,
        max: 0,
        percentage: 0,
        remaining: 0,
        canPerform: false,
        message: 'Limit information unavailable'
      }
    }
    
    const limit = limits[limitType]
    const current = limit.current || 0
    const max = limit.max || 1
    const percentage = getUsagePercentage(limitType)
    const remaining = max - current
    
    let status = 'normal'
    let message = `${current} of ${max} used`
    
    if (isAtLimit(limitType)) {
      status = 'at_limit'
      message = 'Limit reached'
    } else if (isNearLimit(limitType)) {
      status = 'near_limit'
      message = `${remaining} remaining`
    }
    
    return {
      status,
      current,
      max,
      percentage,
      remaining,
      canPerform: canPerformAction(limitType),
      message
    }
  }, [limits, getUsagePercentage, isAtLimit, isNearLimit, canPerformAction])
  
  // Feature availability matrix
  const getFeatureMatrix = useCallback(() => {
    const features = Object.values(FEATURE_GATES)
    const matrix = {}
    
    features.forEach(feature => {
      matrix[feature] = {
        available: hasFeature(feature),
        upgradeMessage: hasFeature(feature) ? null : getUpgradeMessage(feature)
      }
    })
    
    return matrix
  }, [hasFeature, getUpgradeMessage])
  
  // Plan summary for display
  const getPlanSummary = useCallback(() => {
    if (!plan) {
      return {
        name: 'Unknown',
        displayName: 'Unknown Plan',
        tier: 'free',
        canUpgrade: true
      }
    }
    
    return {
      name: plan.plan_name,
      displayName: plan.display_name || plan.plan_name,
      tier: plan.plan_name,
      canUpgrade: canUpgrade(),
      features: Object.values(FEATURE_GATES).filter(hasFeature),
      limits: limits ? Object.keys(limits) : []
    }
  }, [plan, limits, canUpgrade, hasFeature])
  
  return {
    // Context data
    plan,
    limits,
    loading,
    error,
    conditionals,
    
    // Feature checking
    hasFeature,
    hasPlanTier,
    canPerformAction,
    checkMultipleFeatures,
    
    // Usage monitoring
    getUsagePercentage,
    isNearLimit,
    isAtLimit,
    getLimitStatus,
    
    // Upgrade utilities
    getUpgradeMessage,
    canUpgrade,
    
    // UI utilities
    shouldShowNavItem,
    getButtonState,
    getPlanAwareStyles,
    
    // Summary utilities
    getFeatureMatrix,
    getPlanSummary,
    
    // Quick access to common checks
    hasFullAI: () => hasFeature(FEATURE_GATES.FULL_AI),
    hasPremiumAI: () => hasFeature(FEATURE_GATES.PREMIUM_AI),
    hasAIInbox: () => hasFeature(FEATURE_GATES.AI_INBOX),
    hasEnhancedAutopilot: () => hasFeature(FEATURE_GATES.ENHANCED_AUTOPILOT),
    hasAdvancedAnalytics: () => hasFeature(FEATURE_GATES.ADVANCED_ANALYTICS),
    hasPredictiveAnalytics: () => hasFeature(FEATURE_GATES.PREDICTIVE_ANALYTICS),
    hasCRMIntegration: () => hasFeature(FEATURE_GATES.CRM_INTEGRATION),
    hasWhiteLabel: () => hasFeature(FEATURE_GATES.WHITE_LABEL),
    
    // Plan tier checks
    isFree: () => hasPlanTier('free'),
    isStarter: () => hasPlanTier('starter'),
    isPro: () => hasPlanTier('pro'),
    isEnterprise: () => hasPlanTier('enterprise'),
    
    // Usage limit quick checks
    canCreatePost: () => canPerformAction(USAGE_LIMITS.POSTS, 'create'),
    canGenerateImage: () => canPerformAction(USAGE_LIMITS.IMAGES, 'generate'),
    canAddProfile: () => canPerformAction(USAGE_LIMITS.SOCIAL_PROFILES, 'add'),
    canInviteUser: () => canPerformAction(USAGE_LIMITS.TEAM_MEMBERS, 'add'),
    
    // Usage status quick checks
    postsNearLimit: () => isNearLimit(USAGE_LIMITS.POSTS),
    imagesNearLimit: () => isNearLimit(USAGE_LIMITS.IMAGES),
    profilesNearLimit: () => isNearLimit(USAGE_LIMITS.SOCIAL_PROFILES),
    
    postsAtLimit: () => isAtLimit(USAGE_LIMITS.POSTS),
    imagesAtLimit: () => isAtLimit(USAGE_LIMITS.IMAGES),
    profilesAtLimit: () => isAtLimit(USAGE_LIMITS.SOCIAL_PROFILES)
  }
}

/**
 * Hook for plan-aware form validation
 */
export const usePlanValidation = () => {
  const { canPerformAction, getUpgradeMessage, isAtLimit } = usePlanConditionals()
  
  const validateAction = useCallback((limitType, action = 'create') => {
    const canPerform = canPerformAction(limitType, action)
    const atLimit = isAtLimit(limitType)
    
    return {
      valid: canPerform,
      blocked: !canPerform,
      error: !canPerform ? `Cannot perform action: ${limitType} limit reached` : null,
      upgradeMessage: !canPerform ? getUpgradeMessage(limitType) : null,
      atLimit
    }
  }, [canPerformAction, isAtLimit, getUpgradeMessage])
  
  return {
    validateAction,
    validatePostCreation: () => validateAction(USAGE_LIMITS.POSTS, 'create'),
    validateImageGeneration: () => validateAction(USAGE_LIMITS.IMAGES, 'generate'),
    validateProfileConnection: () => validateAction(USAGE_LIMITS.SOCIAL_PROFILES, 'add')
  }
}

/**
 * Hook for plan-aware navigation
 */
export const usePlanNavigation = () => {
  const { shouldShowNavItem, hasFeature, hasPlanTier } = usePlanConditionals()
  
  const getNavigationItems = useCallback((navigationConfig) => {
    return navigationConfig.filter(item => shouldShowNavItem(item))
  }, [shouldShowNavItem])
  
  const canAccessRoute = useCallback((routeConfig) => {
    return shouldShowNavItem(routeConfig)
  }, [shouldShowNavItem])
  
  return {
    getNavigationItems,
    canAccessRoute,
    shouldShowNavItem
  }
}

export default usePlanConditionals