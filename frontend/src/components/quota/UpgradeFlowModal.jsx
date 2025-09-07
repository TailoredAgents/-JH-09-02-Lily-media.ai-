import React, { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { usePlan } from '../../contexts/PlanContext'
import { usePlanConditionals } from '../../hooks/usePlanConditionals'
import { useNotifications } from '../../hooks/useNotifications'
import api from '../../services/api'
import {
  XMarkIcon,
  ArrowUpIcon,
  CheckIcon,
  StarIcon,
  LockClosedIcon,
  ChartBarIcon,
  CreditCardIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

/**
 * Comprehensive Upgrade Flow Modal
 *
 * Provides contextual upgrade flows based on user needs
 * with smart plan recommendations and feature comparisons
 */
const UpgradeFlowModal = ({
  isOpen,
  onClose,
  triggerContext = null, // { action, limitType, currentUsage }
  recommendedPlan = null,
  showComparison = true,
  trackingSource = 'quota_modal',
}) => {
  const { plan: currentPlan, refreshPlan } = usePlan()
  const { canUpgrade, getUpgradeMessage } = usePlanConditionals()
  const { showSuccess, showError } = useNotifications()

  const [availablePlans, setAvailablePlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState(null)
  const [annualBilling, setAnnualBilling] = useState(false)
  const [selectedPlan, setSelectedPlan] = useState(null)

  useEffect(() => {
    if (isOpen) {
      loadPlans()
    }
  }, [isOpen])

  const loadPlans = async () => {
    try {
      setLoading(true)
      const response = await api.request('/api/billing/plans')
      const plans = response.plans || []

      setAvailablePlans(plans)

      // Auto-select recommended plan or next tier up
      if (recommendedPlan) {
        const recommended = plans.find((p) => p.name === recommendedPlan)
        setSelectedPlan(recommended)
      } else if (currentPlan) {
        const planHierarchy = ['free', 'starter', 'pro', 'enterprise']
        const currentIndex = planHierarchy.indexOf(currentPlan.plan_name)
        const nextPlan = plans.find(
          (p) => planHierarchy.indexOf(p.name) === currentIndex + 1
        )
        setSelectedPlan(nextPlan || plans[0])
      } else {
        setSelectedPlan(plans[0])
      }
    } catch (error) {
      console.error('Failed to load plans:', error)
      showError('Failed to load available plans')
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async (planName) => {
    if (!planName || checkoutLoading) return

    setCheckoutLoading(planName)
    try {
      const response = await api.request('/api/billing/checkout', {
        method: 'POST',
        body: {
          plan_name: planName,
          annual_billing: annualBilling,
          success_url: `${window.location.origin}/billing?success=true`,
          cancel_url: `${window.location.origin}/billing?cancelled=true`,
          metadata: {
            upgrade_source: trackingSource,
            trigger_context: triggerContext
              ? JSON.stringify(triggerContext)
              : null,
            current_plan: currentPlan?.plan_name || 'free',
          },
        },
      })

      // Track upgrade initiation
      if (window.gtag) {
        window.gtag('event', 'begin_checkout', {
          event_category: 'upgrade_flow',
          event_label: `${trackingSource}_${planName}`,
          value: response.amount / 100,
          custom_parameters: {
            trigger_context: triggerContext?.limitType || 'unknown',
            current_plan: currentPlan?.plan_name || 'free',
          },
        })
      }

      // Close modal and redirect to checkout
      onClose()
      window.location.href = response.checkout_url
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      showError(
        error.response?.data?.detail || 'Failed to start upgrade process'
      )
    } finally {
      setCheckoutLoading(null)
    }
  }

  const getPlanIcon = (planName) => {
    switch (planName.toLowerCase()) {
      case 'starter':
        return ChartBarIcon
      case 'pro':
        return StarIcon
      case 'enterprise':
        return ShieldCheckIcon
      default:
        return SparklesIcon
    }
  }

  const getPlanColor = (planName) => {
    switch (planName.toLowerCase()) {
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

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const getContextualMessage = () => {
    if (!triggerContext) return null

    const { action, limitType, currentUsage } = triggerContext

    switch (limitType) {
      case 'posts':
        return {
          title: "You've reached your daily post limit",
          description:
            'Upgrade to post more content and grow your audience faster',
          benefit: 'Get up to unlimited daily posts',
        }
      case 'images':
        return {
          title: "You've used all your AI image generations",
          description:
            'Upgrade to create more stunning visuals for your content',
          benefit: 'Get up to 1,000+ monthly images',
        }
      case 'social_profiles':
        return {
          title: "You've connected all available social profiles",
          description: 'Upgrade to manage more social media accounts',
          benefit: 'Connect unlimited social profiles',
        }
      default:
        return null
    }
  }

  const contextMessage = getContextualMessage()
  const filteredPlans = availablePlans.filter(
    (p) => !currentPlan || p.name !== currentPlan.plan_name
  )

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 p-6 text-left align-middle shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <Dialog.Title
                      as="h3"
                      className="text-2xl font-semibold leading-6 text-gray-900 dark:text-white flex items-center"
                    >
                      <ArrowUpIcon className="h-6 w-6 mr-2 text-blue-600" />
                      {contextMessage?.title || 'Upgrade Your Plan'}
                    </Dialog.Title>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      {contextMessage?.description ||
                        'Choose a plan that fits your needs and unlock more features'}
                    </p>
                  </div>

                  <button
                    type="button"
                    className="rounded-md bg-white dark:bg-gray-800 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onClick={onClose}
                  >
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>

                {/* Context Benefit */}
                {contextMessage?.benefit && (
                  <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <div className="flex items-center">
                      <SparklesIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2" />
                      <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        {contextMessage.benefit}
                      </p>
                    </div>
                  </div>
                )}

                {/* Billing Toggle */}
                <div className="flex justify-center mb-6">
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
                {loading ? (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="animate-pulse">
                        <div className="bg-gray-200 rounded-lg h-64"></div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                    {filteredPlans.slice(0, 3).map((planData) => {
                      const PlanIcon = getPlanIcon(planData.name)
                      const isSelected = selectedPlan?.name === planData.name
                      const isPopular = planData.name === 'pro'

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
                          className={`relative bg-white dark:bg-gray-800 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                            isSelected
                              ? 'border-blue-500 dark:border-blue-400 shadow-lg'
                              : isPopular
                                ? 'border-purple-300 dark:border-purple-600 hover:border-purple-400 dark:hover:border-purple-500'
                                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                          }`}
                          onClick={() => setSelectedPlan(planData)}
                        >
                          {/* Popular badge */}
                          {isPopular && (
                            <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                                <StarIcon className="w-3 h-3 mr-1" />
                                Recommended
                              </span>
                            </div>
                          )}

                          <div className="p-6">
                            {/* Plan header */}
                            <div className="text-center mb-4">
                              <div
                                className={`inline-flex p-3 rounded-lg mb-3 ${getPlanColor(planData.name)}`}
                              >
                                <PlanIcon className="w-6 h-6" />
                              </div>
                              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                                {planData.display_name}
                              </h3>
                              <div className="mb-2">
                                {originalPrice && (
                                  <span className="text-sm text-gray-500 dark:text-gray-400 line-through mr-2">
                                    {formatPrice(originalPrice)}
                                  </span>
                                )}
                                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                                  {formatPrice(price)}
                                </span>
                                <span className="text-gray-600 dark:text-gray-400">
                                  /{annualBilling ? 'year' : 'month'}
                                </span>
                              </div>
                            </div>

                            {/* Key features */}
                            <ul className="space-y-2 text-sm">
                              {planData.limits?.max_posts_per_day && (
                                <li className="flex items-center">
                                  <CheckIcon className="w-4 h-4 text-green-500 mr-2" />
                                  <span className="text-gray-700 dark:text-gray-300">
                                    {planData.limits.max_posts_per_day} posts
                                    per day
                                  </span>
                                </li>
                              )}
                              {planData.limits?.image_generation_limit && (
                                <li className="flex items-center">
                                  <CheckIcon className="w-4 h-4 text-green-500 mr-2" />
                                  <span className="text-gray-700 dark:text-gray-300">
                                    {planData.limits.image_generation_limit} AI
                                    images per month
                                  </span>
                                </li>
                              )}
                              {planData.limits?.max_social_profiles && (
                                <li className="flex items-center">
                                  <CheckIcon className="w-4 h-4 text-green-500 mr-2" />
                                  <span className="text-gray-700 dark:text-gray-300">
                                    {planData.limits.max_social_profiles} social
                                    profiles
                                  </span>
                                </li>
                              )}
                              {planData.features?.includes(
                                'premium_ai_models'
                              ) && (
                                <li className="flex items-center">
                                  <CheckIcon className="w-4 h-4 text-green-500 mr-2" />
                                  <span className="text-gray-700 dark:text-gray-300">
                                    Premium AI models
                                  </span>
                                </li>
                              )}
                            </ul>
                          </div>

                          {/* Selection indicator */}
                          {isSelected && (
                            <div className="absolute top-4 right-4">
                              <CheckCircleIcon className="w-6 h-6 text-blue-600" />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                    <CreditCardIcon className="h-4 w-4 mr-1" />
                    Secure payment by Stripe • Cancel anytime
                  </div>

                  <div className="flex space-x-3">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                    >
                      Cancel
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        selectedPlan && handleUpgrade(selectedPlan.name)
                      }
                      disabled={!selectedPlan || checkoutLoading}
                      className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {checkoutLoading ? (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Processing...
                        </div>
                      ) : (
                        <>
                          <ArrowUpIcon className="w-4 h-4 mr-2 inline" />
                          Upgrade to{' '}
                          {selectedPlan?.display_name || 'Selected Plan'}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

export default UpgradeFlowModal
