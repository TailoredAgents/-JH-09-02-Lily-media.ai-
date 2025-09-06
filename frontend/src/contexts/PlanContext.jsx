import React, { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import api from '../services/api'

const PlanContext = createContext(null)

export const usePlan = () => {
  const context = useContext(PlanContext)
  if (!context) {
    throw new Error('usePlan must be used within a PlanProvider')
  }
  return context
}

export const PlanProvider = ({ children }) => {
  const { isAuthenticated } = useAuth()
  const [planData, setPlanData] = useState(null)
  const [limits, setLimits] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchPlanData = async () => {
    if (!isAuthenticated) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      const [planResponse, limitsResponse] = await Promise.all([
        api.request('/api/plans/my-plan'),
        api.request('/api/plans/limits'),
      ])

      setPlanData(planResponse)
      setLimits(limitsResponse)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch plan data:', err)
      setError(err.response?.data?.detail || 'Failed to load plan information')

      // Set fallback data for free tier if API fails
      setPlanData({
        plan_name: 'free',
        display_name: 'Free',
        max_social_profiles: 1,
        max_posts_per_day: 3,
        max_posts_per_week: 10,
        image_generation_limit: 5,
        full_ai: false,
        premium_ai_models: false,
        enhanced_autopilot: false,
        ai_inbox: false,
        crm_integration: false,
        advanced_analytics: false,
        predictive_analytics: false,
        white_label: false,
        autopilot_posts_per_day: 0,
        autopilot_research_enabled: false,
        autopilot_ad_campaigns: false,
        max_users: 1,
        max_workspaces: 1,
      })
      setLimits({
        plan: 'free',
        social_profiles: { max: 1, can_add_more: false },
        posts: {
          daily_limit: 3,
          weekly_limit: 10,
          can_post_today: true,
          can_post_this_week: true,
        },
        images: { monthly_limit: 5, can_generate: true },
        autopilot: {
          daily_posts: 0,
          research_enabled: false,
          ad_campaigns: false,
        },
        team: { max_users: 1, max_workspaces: 1 },
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPlanData()
  }, [isAuthenticated])

  const checkFeature = (featureName) => {
    if (!planData) return false
    return planData[featureName] === true
  }

  const checkLimit = (limitType, action = null) => {
    if (!limits) return false

    const limit = limits[limitType]
    if (!limit) return false

    switch (action) {
      case 'can_add':
        return limit.can_add_more || false
      case 'can_post_today':
        return limit.can_post_today || false
      case 'can_post_week':
        return limit.can_post_this_week || false
      case 'can_generate':
        return limit.can_generate || false
      default:
        return limit.max > 0
    }
  }

  const isPlanTier = (tierName) => {
    if (!planData) return false
    return planData.plan_name === tierName
  }

  const canUpgrade = () => {
    if (!planData) return true
    return !isPlanTier('enterprise')
  }

  const getUpgradeMessage = (requiredFeature) => {
    if (!planData) return 'Please upgrade to access this feature.'

    const planTiers = {
      free: 'Starter',
      starter: 'Pro',
      pro: 'Enterprise',
    }

    const nextTier = planTiers[planData.plan_name]
    return nextTier
      ? `Upgrade to ${nextTier} to access ${requiredFeature}.`
      : 'This feature is available in higher-tier plans.'
  }

  const contextValue = {
    // Plan data
    plan: planData,
    limits,
    loading,
    error,

    // Helper methods
    checkFeature,
    checkLimit,
    isPlanTier,
    canUpgrade,
    getUpgradeMessage,

    // Refresh functionality
    refreshPlan: fetchPlanData,

    // Quick feature checks
    hasFullAI: () => checkFeature('full_ai'),
    hasPremiumAI: () => checkFeature('premium_ai_models'),
    hasEnhancedAutopilot: () => checkFeature('enhanced_autopilot'),
    hasAIInbox: () => checkFeature('ai_inbox'),
    hasCRMIntegration: () => checkFeature('crm_integration'),
    hasAdvancedAnalytics: () => checkFeature('advanced_analytics'),
    hasPredictiveAnalytics: () => checkFeature('predictive_analytics'),
    hasWhiteLabel: () => checkFeature('white_label'),

    // Quick limit checks
    canAddProfile: () => checkLimit('social_profiles', 'can_add'),
    canPostToday: () => checkLimit('posts', 'can_post_today'),
    canPostThisWeek: () => checkLimit('posts', 'can_post_week'),
    canGenerateImage: () => checkLimit('images', 'can_generate'),
  }

  return (
    <PlanContext.Provider value={contextValue}>{children}</PlanContext.Provider>
  )
}
