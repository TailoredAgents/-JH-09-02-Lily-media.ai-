import React, { useState, useEffect } from 'react'
import { usePlan } from '../contexts/PlanContext'
import { useAuth } from '../contexts/AuthContext'
import { useNotifications } from '../hooks/useNotifications'
import api from '../services/api'
import {
  CreditCardIcon,
  CheckIcon,
  XMarkIcon,
  ArrowUpIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  UserIcon,
  ChartBarIcon,
  CloudIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  EyeIcon,
  StarIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

const Billing = () => {
  const { plan, limits, refreshPlan, canUpgrade } = usePlan()
  const { user } = useAuth()
  const { showSuccess, showError, showInfo } = useNotifications()

  const [availablePlans, setAvailablePlans] = useState([])
  const [billingInfo, setBillingInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState(null)
  const [portalLoading, setPortalLoading] = useState(false)
  const [annualBilling, setAnnualBilling] = useState(false)

  useEffect(() => {
    loadBillingData()
  }, [])

  const loadBillingData = async () => {
    try {
      setLoading(true)
      const [plansResponse, billingResponse] = await Promise.all([
        api.request('/api/billing/plans'),
        api.request('/api/billing/info').catch(() => ({ data: null })),
      ])

      setAvailablePlans(plansResponse.plans || [])
      setBillingInfo(billingResponse || null)
    } catch (error) {
      console.error('Failed to load billing data:', error)
      showError('Failed to load billing information')
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async (planName) => {
    if (checkoutLoading) return

    setCheckoutLoading(planName)
    try {
      const response = await api.request('/api/billing/checkout', {
        method: 'POST',
        body: {
          plan_name: planName,
          annual_billing: annualBilling,
          success_url: `${window.location.origin}/billing?success=true`,
          cancel_url: `${window.location.origin}/billing?cancelled=true`,
        },
      })

      // Redirect to Stripe checkout
      window.location.href = response.checkout_url
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      showError(
        error.response?.data?.detail || 'Failed to start checkout process'
      )
    } finally {
      setCheckoutLoading(null)
    }
  }

  const handleManageSubscription = async () => {
    if (portalLoading) return

    setPortalLoading(true)
    try {
      const response = await api.request('/api/billing/customer-portal', {
        method: 'POST',
        body: {
          return_url: window.location.href,
        },
      })

      window.location.href = response.portal_url
    } catch (error) {
      console.error('Failed to open customer portal:', error)
      showError(
        error.response?.data?.detail || 'Failed to open subscription management'
      )
    } finally {
      setPortalLoading(false)
    }
  }

  const getPlanIcon = (planName) => {
    switch (planName.toLowerCase()) {
      case 'free':
        return EyeIcon
      case 'starter':
        return UserIcon
      case 'pro':
        return ChartBarIcon
      case 'enterprise':
        return ShieldCheckIcon
      default:
        return DocumentTextIcon
    }
  }

  const getPlanColor = (planName) => {
    switch (planName.toLowerCase()) {
      case 'free':
        return 'text-gray-600 bg-gray-100 border-gray-200'
      case 'starter':
        return 'text-blue-600 bg-blue-100 border-blue-200'
      case 'pro':
        return 'text-purple-600 bg-purple-100 border-purple-200'
      case 'enterprise':
        return 'text-yellow-600 bg-yellow-100 border-yellow-200'
      default:
        return 'text-gray-600 bg-gray-100 border-gray-200'
    }
  }

  const isCurrentPlan = (planName) => {
    return plan?.plan_name === planName
  }

  const canUpgradeToPlan = (targetPlan) => {
    if (!plan) return true

    const planHierarchy = ['free', 'starter', 'pro', 'enterprise']
    const currentIndex = planHierarchy.indexOf(plan.plan_name)
    const targetIndex = planHierarchy.indexOf(targetPlan.name)

    return targetIndex > currentIndex
  }

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const getFeatureList = (planData) => {
    const features = []

    if (planData.limits?.max_social_profiles) {
      features.push(
        `${planData.limits.max_social_profiles} social profile${planData.limits.max_social_profiles === 1 ? '' : 's'}`
      )
    }

    if (planData.limits?.max_posts_per_day) {
      features.push(`${planData.limits.max_posts_per_day} posts per day`)
    }

    if (planData.features?.includes('full_ai')) {
      features.push('Full AI capabilities')
    }

    if (planData.features?.includes('premium_ai_models')) {
      features.push('Premium AI models')
    }

    if (planData.features?.includes('enhanced_autopilot')) {
      features.push('Enhanced Autopilot')
    }

    if (planData.features?.includes('advanced_analytics')) {
      features.push('Advanced Analytics')
    }

    if (planData.features?.includes('ai_inbox')) {
      features.push('AI Inbox')
    }

    if (planData.features?.includes('crm_integration')) {
      features.push('CRM Integration')
    }

    return features.slice(0, 6) // Limit to 6 features for display
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">
          Loading billing information...
        </span>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          Plans & Billing
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Choose the perfect plan for your social media management needs.
          Upgrade or downgrade anytime.
        </p>
      </div>

      {/* Current Plan Status */}
      {plan && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-8 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className={`p-3 rounded-lg ${getPlanColor(plan.plan_name)}`}>
                {React.createElement(getPlanIcon(plan.plan_name), {
                  className: 'h-6 w-6',
                })}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Current Plan: {plan.display_name || plan.plan_name}
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {billingInfo?.subscription_status === 'active'
                    ? 'Active subscription'
                    : billingInfo?.subscription_status === 'trialing'
                      ? 'Free trial active'
                      : 'Free plan'}
                </p>
              </div>
            </div>

            {billingInfo?.stripe_customer_id && (
              <button
                onClick={handleManageSubscription}
                disabled={portalLoading}
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <CreditCardIcon className="w-4 h-4 mr-2" />
                {portalLoading ? 'Loading...' : 'Manage Subscription'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Billing Toggle */}
      <div className="flex justify-center mb-8">
        <div className="bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setAnnualBilling(false)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                !annualBilling
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnualBilling(true)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                annualBilling
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Annual
              <span className="ml-1 text-xs text-green-600 font-semibold">
                Save 20%
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
        {availablePlans.map((planData, index) => {
          const PlanIcon = getPlanIcon(planData.name)
          const isPopular = planData.name === 'pro'
          const currentPlan = isCurrentPlan(planData.name)
          const canUpgradeThis = canUpgradeToPlan(planData)
          const features = getFeatureList(planData)

          const price =
            annualBilling && planData.annual_price
              ? planData.annual_price
              : planData.monthly_price

          const originalPrice =
            annualBilling && planData.annual_price
              ? planData.monthly_price * 12
              : null

          return (
            <div
              key={planData.id}
              className={`relative bg-white dark:bg-gray-800 rounded-lg shadow-sm border-2 transition-all duration-200 hover:shadow-md ${
                isPopular
                  ? 'border-purple-500 dark:border-purple-400'
                  : currentPlan
                    ? 'border-green-500 dark:border-green-400'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              {/* Popular badge */}
              {isPopular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                    <StarIcon className="w-3 h-3 mr-1" />
                    Most Popular
                  </span>
                </div>
              )}

              {/* Current plan badge */}
              {currentPlan && (
                <div className="absolute -top-3 right-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                    <CheckCircleIcon className="w-3 h-3 mr-1" />
                    Current Plan
                  </span>
                </div>
              )}

              <div className="p-6">
                {/* Plan header */}
                <div className="text-center mb-6">
                  <div
                    className={`inline-flex p-3 rounded-lg mb-4 ${getPlanColor(planData.name)}`}
                  >
                    <PlanIcon className="w-6 h-6" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    {planData.display_name}
                  </h3>
                  <div className="mb-4">
                    {originalPrice && (
                      <span className="text-sm text-gray-500 dark:text-gray-400 line-through mr-2">
                        {formatPrice(originalPrice)}
                      </span>
                    )}
                    <span className="text-3xl font-bold text-gray-900 dark:text-white">
                      {formatPrice(price)}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      /{annualBilling ? 'year' : 'month'}
                    </span>
                  </div>
                  {planData.description && (
                    <p className="text-gray-600 dark:text-gray-400 text-sm">
                      {planData.description}
                    </p>
                  )}
                </div>

                {/* Features list */}
                <ul className="space-y-3 mb-6">
                  {features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-start">
                      <CheckIcon className="w-5 h-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700 dark:text-gray-300 text-sm">
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* Action button */}
                <div className="mt-6">
                  {currentPlan ? (
                    <button
                      disabled
                      className="w-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 py-3 px-4 rounded-lg font-medium cursor-not-allowed"
                    >
                      Current Plan
                    </button>
                  ) : canUpgradeThis ? (
                    <button
                      onClick={() => handleUpgrade(planData.name)}
                      disabled={checkoutLoading === planData.name}
                      className={`w-full py-3 px-4 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                        isPopular
                          ? 'bg-purple-600 hover:bg-purple-700 text-white focus:ring-purple-500'
                          : 'bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {checkoutLoading === planData.name ? (
                        <div className="flex items-center justify-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Processing...
                        </div>
                      ) : (
                        <>
                          <ArrowUpIcon className="w-4 h-4 mr-2 inline" />
                          Upgrade to {planData.display_name}
                        </>
                      )}
                    </button>
                  ) : (
                    <button
                      disabled
                      className="w-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 py-3 px-4 rounded-lg font-medium cursor-not-allowed"
                    >
                      Not Available
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Usage overview */}
      {limits && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Current Usage & Limits
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="bg-blue-100 dark:bg-blue-900 p-3 rounded-lg w-12 h-12 mx-auto mb-3 flex items-center justify-center">
                <DocumentTextIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {limits.posts?.daily_limit || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Posts per day
              </div>
            </div>

            <div className="text-center">
              <div className="bg-green-100 dark:bg-green-900 p-3 rounded-lg w-12 h-12 mx-auto mb-3 flex items-center justify-center">
                <CloudIcon className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {limits.images?.monthly_limit || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Images per month
              </div>
            </div>

            <div className="text-center">
              <div className="bg-purple-100 dark:bg-purple-900 p-3 rounded-lg w-12 h-12 mx-auto mb-3 flex items-center justify-center">
                <UserIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {limits.social_profiles?.max || 1}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Social profiles
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Billing
