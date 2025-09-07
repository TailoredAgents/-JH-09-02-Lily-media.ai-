/**
 * Plan-based conditional rendering utilities
 * 
 * This module provides utilities for conditional rendering based on user plans,
 * features, and usage limits to ensure consistent plan enforcement across the UI.
 */

// Plan tier hierarchy for comparison
const PLAN_HIERARCHY = {
  free: 0,
  starter: 1,
  pro: 2,
  enterprise: 3
}

/**
 * Advanced plan-based conditional utilities
 */
export class PlanConditionals {
  constructor(planData, limits) {
    this.plan = planData
    this.limits = limits
  }

  /**
   * Check if user has access to a feature
   * @param {string} featureName - Name of the feature to check
   * @returns {boolean} - Whether user has access
   */
  hasFeature(featureName) {
    if (!this.plan) return false
    return this.plan[featureName] === true
  }

  /**
   * Check if user's plan tier meets minimum requirement
   * @param {string} requiredTier - Minimum tier required
   * @returns {boolean} - Whether user meets tier requirement
   */
  hasPlanTier(requiredTier) {
    if (!this.plan) return false
    const currentLevel = PLAN_HIERARCHY[this.plan.plan_name] || 0
    const requiredLevel = PLAN_HIERARCHY[requiredTier] || 0
    return currentLevel >= requiredLevel
  }

  /**
   * Check usage limits with various conditions
   * @param {string} limitType - Type of limit to check
   * @param {string} action - Specific action to validate
   * @returns {boolean} - Whether action is allowed
   */
  canPerformAction(limitType, action = 'default') {
    if (!this.limits || !this.limits[limitType]) return false

    const limit = this.limits[limitType]
    
    switch (action) {
      case 'create':
      case 'add':
        return limit.can_add_more !== false
      case 'post_today':
        return limit.can_post_today !== false
      case 'post_week':
        return limit.can_post_this_week !== false
      case 'generate':
        return limit.can_generate !== false
      default:
        return (limit.current || 0) < (limit.max || 0)
    }
  }

  /**
   * Get usage percentage for display
   * @param {string} limitType - Type of limit
   * @returns {number} - Usage percentage (0-100)
   */
  getUsagePercentage(limitType) {
    if (!this.limits || !this.limits[limitType]) return 0
    
    const limit = this.limits[limitType]
    const current = limit.current || 0
    const max = limit.max || 1
    
    return Math.min((current / max) * 100, 100)
  }

  /**
   * Check if usage is near limit (75% or higher)
   * @param {string} limitType - Type of limit
   * @returns {boolean} - Whether near limit
   */
  isNearLimit(limitType) {
    return this.getUsagePercentage(limitType) >= 75
  }

  /**
   * Check if usage is at limit (90% or higher)
   * @param {string} limitType - Type of limit  
   * @returns {boolean} - Whether at limit
   */
  isAtLimit(limitType) {
    return this.getUsagePercentage(limitType) >= 90
  }

  /**
   * Get appropriate upgrade message based on current plan
   * @param {string} feature - Feature or limit being requested
   * @returns {string} - Upgrade message
   */
  getUpgradeMessage(feature) {
    if (!this.plan) return `Upgrade your plan to access ${feature}`

    const planTiers = {
      free: { next: 'Starter', price: '$9/month' },
      starter: { next: 'Pro', price: '$29/month' },
      pro: { next: 'Enterprise', price: '$99/month' }
    }

    const currentPlan = this.plan.plan_name
    const nextTier = planTiers[currentPlan]

    if (nextTier) {
      return `Upgrade to ${nextTier.next} (${nextTier.price}) to access ${feature}`
    }

    return `${feature} requires a higher-tier plan`
  }

  /**
   * Determine if upgrade is possible
   * @returns {boolean} - Whether user can upgrade
   */
  canUpgrade() {
    if (!this.plan) return true
    return this.plan.plan_name !== 'enterprise'
  }
}

/**
 * Feature-specific conditional checks
 */
export const FEATURE_GATES = {
  // Content features
  FULL_AI: 'full_ai',
  PREMIUM_AI: 'premium_ai_models',
  AI_INBOX: 'ai_inbox',
  ENHANCED_AUTOPILOT: 'enhanced_autopilot',
  
  // Integration features
  CRM_INTEGRATION: 'crm_integration',
  WHITE_LABEL: 'white_label',
  
  // Analytics features
  ADVANCED_ANALYTICS: 'advanced_analytics',
  PREDICTIVE_ANALYTICS: 'predictive_analytics'
}

/**
 * Plan tier requirements for specific features
 */
export const TIER_REQUIREMENTS = {
  // Basic features - available to all
  CONTENT_CREATION: 'free',
  BASIC_SCHEDULING: 'free',
  BASIC_ANALYTICS: 'free',
  
  // Premium features
  AI_INBOX: 'starter',
  PREMIUM_AI: 'starter', 
  MULTI_WORKSPACE: 'pro',
  WHITE_LABEL: 'enterprise',
  CUSTOM_INTEGRATIONS: 'enterprise'
}

/**
 * Usage limit types
 */
export const USAGE_LIMITS = {
  POSTS: 'posts',
  IMAGES: 'images', 
  SOCIAL_PROFILES: 'social_profiles',
  TEAM_MEMBERS: 'team',
  WORKSPACES: 'workspaces',
  AUTOPILOT: 'autopilot'
}

/**
 * Helper function to create plan conditionals instance
 * @param {Object} plan - Plan data
 * @param {Object} limits - Usage limits
 * @returns {PlanConditionals} - Conditionals instance
 */
export function createPlanConditionals(plan, limits) {
  return new PlanConditionals(plan, limits)
}

/**
 * HOC for plan-based conditional rendering
 * Note: This function should be used in JSX files, not here
 * @param {React.Component} Component - Component to wrap
 * @param {Object} conditions - Conditional requirements
 * @returns {React.Component} - Wrapped component
 */
export function withPlanConditional(Component, conditions = {}) {
  // This is a utility function that returns a component factory
  // The actual JSX should be handled in .jsx files
  return {
    Component,
    conditions,
    // Helper to check if conditions are met
    checkConditions: (plan, limits) => {
      const conditionals = createPlanConditionals(plan, limits)
      
      if (conditions.feature && !conditionals.hasFeature(conditions.feature)) {
        return { hasAccess: false, reason: 'feature_required' }
      }
      
      if (conditions.tier && !conditionals.hasPlanTier(conditions.tier)) {
        return { hasAccess: false, reason: 'tier_required' }
      }
      
      if (conditions.limit && !conditionals.canPerformAction(conditions.limit, conditions.action)) {
        return { hasAccess: false, reason: 'limit_exceeded' }
      }
      
      return { hasAccess: true }
    }
  }
}

/**
 * Plan-aware visibility utilities
 */
export const planVisibility = {
  /**
   * Show component only if user has specific feature
   */
  showForFeature: (feature, plan) => {
    return plan && plan[feature] === true
  },
  
  /**
   * Show component only if user meets tier requirement
   */
  showForTier: (requiredTier, plan) => {
    if (!plan) return false
    const currentLevel = PLAN_HIERARCHY[plan.plan_name] || 0
    const requiredLevel = PLAN_HIERARCHY[requiredTier] || 0
    return currentLevel >= requiredLevel
  },
  
  /**
   * Show component based on usage limits
   */
  showForUsage: (limitType, limits) => {
    if (!limits || !limits[limitType]) return false
    const limit = limits[limitType]
    return (limit.current || 0) < (limit.max || 0)
  },
  
  /**
   * Hide component if usage is at limit
   */
  hideAtLimit: (limitType, limits) => {
    if (!limits || !limits[limitType]) return true
    const limit = limits[limitType]
    const percentage = ((limit.current || 0) / (limit.max || 1)) * 100
    return percentage < 90
  }
}

export default PlanConditionals