import React, { useState } from 'react'
import { usePlan } from '../contexts/PlanContext'
import { useAuth } from '../contexts/AuthContext'
import { useNotifications } from '../hooks/useNotifications'
import api from '../services/api'
import {
  XMarkIcon,
  CheckIcon,
  ArrowUpIcon,
  StarIcon,
  BoltIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  ChartBarIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

const UpgradeFlow = ({
  isOpen,
  onClose,
  triggerFeature = null,
  currentLimitType = null,
}) => {
  const { plan, canUpgrade, getUpgradeMessage } = usePlan()
  const { user } = useAuth()
  const { showSuccess, showError } = useNotifications()
  const [loading, setLoading] = useState(null)
  const [selectedBilling, setSelectedBilling] = useState('monthly')

  const plans = [
    {
      name: 'starter',
      display_name: 'Starter',
      monthly_price: 29,
      annual_price: 24,
      icon: UserGroupIcon,
      color: 'blue',
      popular: false,
      features: [
        'Up to 10 posts per day',
        'Basic AI content generation',
        '3 social profiles',
        '50 images per month',
        'Email support',
        'Basic analytics',
      ],
    },
    {
      name: 'pro',
      display_name: 'Pro',
      monthly_price: 99,
      annual_price: 79,
      icon: ChartBarIcon,
      color: 'purple',
      popular: true,
      features: [
        'Unlimited posts',
        'Premium AI models (GPT-4)',
        'Unlimited social profiles',
        'Unlimited images',
        'AI Social Inbox',
        'Advanced analytics',
        'Priority support',
        'Brand Brain memory',
        'Auto-posting',
      ],
    },
    {
      name: 'enterprise',
      display_name: 'Enterprise',
      monthly_price: 299,
      annual_price: 249,
      icon: ShieldCheckIcon,
      color: 'yellow',
      popular: false,
      features: [
        'Everything in Pro',
        'White-label branding',
        'Team collaboration',
        'Advanced integrations',
        'Dedicated support',
        'Custom AI models',
        'API access',
        'SSO integration',
      ],
    },
  ]

  const handleUpgrade = async (planName) => {
    if (loading) return

    setLoading(planName)
    try {
      const response = await api.request('/api/billing/checkout', {
        method: 'POST',
        body: {
          plan_name: planName,
          annual_billing: selectedBilling === 'annual',
          success_url: `${window.location.origin}/billing?success=true`,
          cancel_url: window.location.href,
        },
      })

      // Redirect to Stripe checkout
      window.location.href = response.checkout_url
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      showError(
        error.response?.data?.detail || 'Failed to start checkout process',
        'Upgrade Error'
      )
    } finally {
      setLoading(null)
    }
  }

  const getPlanIcon = (planData) => {
    return planData.icon
  }

  const getPrice = (planData) => {
    return selectedBilling === 'annual'
      ? planData.annual_price
      : planData.monthly_price
  }

  const canUpgradeTo = (targetPlan) => {
    if (!plan) return true
    const hierarchy = ['free', 'starter', 'pro', 'enterprise']
    const currentIndex = hierarchy.indexOf(plan.plan_name)
    const targetIndex = hierarchy.indexOf(targetPlan.name)
    return targetIndex > currentIndex
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white dark:bg-gray-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Upgrade Your Plan
                </h3>
                {triggerFeature && (
                  <p className="text-blue-100 text-sm mt-1">
                    Unlock {triggerFeature} and more with a premium plan
                  </p>
                )}
                {currentLimitType && (
                  <p className="text-blue-100 text-sm mt-1">
                    You've reached your {currentLimitType} limit. Upgrade for
                    more capacity.
                  </p>
                )}
              </div>
              <button
                onClick={onClose}
                className="text-white hover:text-blue-100 transition-colors"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {/* Billing toggle */}
            <div className="flex justify-center mb-8">
              <div className="bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => setSelectedBilling('monthly')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      selectedBilling === 'monthly'
                        ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    Monthly
                  </button>
                  <button
                    onClick={() => setSelectedBilling('annual')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      selectedBilling === 'annual'
                        ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
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

            {/* Plans grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans.map((planData) => {
                const PlanIcon = getPlanIcon(planData)
                const canUpgradeToThis = canUpgradeTo(planData)
                const isCurrentPlan = plan?.plan_name === planData.name
                const price = getPrice(planData)

                return (
                  <div
                    key={planData.name}
                    className={`relative bg-white dark:bg-gray-800 rounded-lg border-2 ${
                      planData.popular
                        ? 'border-purple-500 shadow-lg'
                        : 'border-gray-200 dark:border-gray-700'
                    } ${isCurrentPlan ? 'ring-2 ring-blue-500' : ''}`}
                  >
                    {planData.popular && (
                      <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                        <span className="bg-purple-500 text-white px-3 py-1 rounded-full text-xs font-semibold">
                          Most Popular
                        </span>
                      </div>
                    )}

                    <div className="p-6">
                      {/* Plan header */}
                      <div className="text-center mb-6">
                        <div
                          className={`inline-flex p-3 rounded-lg bg-${planData.color}-100 dark:bg-${planData.color}-900 mb-4`}
                        >
                          <PlanIcon
                            className={`h-8 w-8 text-${planData.color}-600 dark:text-${planData.color}-400`}
                          />
                        </div>
                        <h4 className="text-xl font-semibold text-gray-900 dark:text-white">
                          {planData.display_name}
                        </h4>
                        <div className="mt-2">
                          <span className="text-3xl font-bold text-gray-900 dark:text-white">
                            ${price}
                          </span>
                          <span className="text-gray-500 dark:text-gray-400">
                            /{selectedBilling === 'annual' ? 'mo' : 'month'}
                          </span>
                          {selectedBilling === 'annual' && (
                            <div className="text-sm text-green-600 font-medium">
                              ${planData.annual_price * 12}/year (save $
                              {(planData.monthly_price -
                                planData.annual_price) *
                                12}
                              )
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Features */}
                      <ul className="space-y-3 mb-8">
                        {planData.features.map((feature, index) => (
                          <li
                            key={index}
                            className="flex items-start space-x-3"
                          >
                            <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              {feature}
                            </span>
                          </li>
                        ))}
                      </ul>

                      {/* CTA button */}
                      {isCurrentPlan ? (
                        <div className="text-center">
                          <div className="inline-flex items-center px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-lg text-sm font-medium">
                            <CheckIcon className="h-4 w-4 mr-2" />
                            Current Plan
                          </div>
                        </div>
                      ) : !canUpgradeToThis ? (
                        <div className="text-center">
                          <div className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded-lg text-sm font-medium">
                            Downgrade not available
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleUpgrade(planData.name)}
                          disabled={loading === planData.name}
                          className={`w-full inline-flex items-center justify-center px-4 py-3 border border-transparent rounded-lg text-sm font-medium transition-colors ${
                            planData.popular
                              ? 'bg-purple-600 text-white hover:bg-purple-700 focus:ring-purple-500'
                              : 'bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-800 hover:bg-gray-700 dark:hover:bg-gray-300 focus:ring-gray-500'
                          } focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50`}
                        >
                          {loading === planData.name ? (
                            <>
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                              Processing...
                            </>
                          ) : (
                            <>
                              <ArrowUpIcon className="h-4 w-4 mr-2" />
                              Upgrade to {planData.display_name}
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Footer note */}
            <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
              <p>
                All plans include a 14-day free trial. Cancel anytime. No setup
                fees.
              </p>
              <p className="mt-1">
                Questions?{' '}
                <a
                  href="mailto:support@lily-ai.com"
                  className="text-blue-600 hover:text-blue-500"
                >
                  Contact support
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UpgradeFlow
