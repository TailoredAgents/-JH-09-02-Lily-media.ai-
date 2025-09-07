import React, { useState, useEffect } from 'react'
import { usePlan } from '../../contexts/PlanContext'
import { useAuth } from '../../contexts/AuthContext'
import { useNotifications } from '../../hooks/useNotifications'
import { usePlanConditionals } from '../../hooks/usePlanConditionals'
import api from '../../services/api'
import StripePortalManager from './StripePortalManager'
import BillingHistory from './BillingHistory'
import { EnhancedUsageIndicator } from '../enhanced/EnhancedPlanGate'
import {
  CreditCardIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  ArrowTrendingUpIcon,
  CalendarDaysIcon,
  BanknotesIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline'
import { CheckCircleIcon as CheckCircleIconSolid } from '@heroicons/react/24/solid'

/**
 * Comprehensive Billing Overview Component
 * 
 * Provides complete billing management with Stripe integration,
 * usage monitoring, and upgrade recommendations
 */
const BillingOverview = () => {
  const { plan, limits, refreshPlan, loading: planLoading } = usePlan()
  const { user } = useAuth()
  const { showSuccess, showError } = useNotifications()
  const { 
    postsNearLimit, 
    imagesNearLimit, 
    profilesNearLimit,
    canUpgrade,
    getUpgradeMessage
  } = usePlanConditionals()
  
  const [billingInfo, setBillingInfo] = useState(null)
  const [upcomingInvoice, setUpcomingInvoice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  
  useEffect(() => {
    loadBillingInfo()
  }, [])
  
  const loadBillingInfo = async () => {
    try {
      setLoading(true)
      const [billingResponse, upcomingResponse] = await Promise.all([
        api.getBillingInfo().catch(() => null),
        api.request('/api/billing/upcoming-invoice').catch(() => null)
      ])
      
      setBillingInfo(billingResponse)
      setUpcomingInvoice(upcomingResponse)
    } catch (error) {
      console.error('Failed to load billing info:', error)
      showError('Failed to load billing information')
    } finally {
      setLoading(false)
    }
  }
  
  const getUsageAlerts = () => {
    const alerts = []
    
    if (postsNearLimit()) {
      alerts.push({
        type: 'warning',
        title: 'Post limit approaching',
        message: 'You\'re near your daily post limit',
        action: 'Upgrade to increase your posting capacity'
      })
    }
    
    if (imagesNearLimit()) {
      alerts.push({
        type: 'warning',
        title: 'Image generation limit approaching',
        message: 'You\'re near your monthly image generation limit',
        action: 'Upgrade for more AI-generated images'
      })
    }
    
    if (profilesNearLimit()) {
      alerts.push({
        type: 'warning',
        title: 'Social profile limit reached',
        message: 'You\'ve reached your social profile limit',
        action: 'Upgrade to connect more social accounts'
      })
    }
    
    return alerts
  }
  
  const getTrialStatus = () => {
    if (!billingInfo || billingInfo.subscription_status !== 'trialing') return null
    
    const trialEnd = billingInfo.trial_end
    if (!trialEnd) return null
    
    const daysLeft = Math.ceil((new Date(trialEnd) - new Date()) / (1000 * 60 * 60 * 24))
    
    return {
      daysLeft: Math.max(0, daysLeft),
      trialEnd: new Date(trialEnd).toLocaleDateString()
    }
  }
  
  const formatAmount = (amount, currency = 'USD') => {
    if (!amount) return '$0.00'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
      minimumFractionDigits: 2
    }).format(amount / 100)
  }
  
  const usageAlerts = getUsageAlerts()
  const trialStatus = getTrialStatus()
  
  if (loading || planLoading) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="h-40 bg-gray-200 rounded-lg"></div>
              <div className="h-60 bg-gray-200 rounded-lg"></div>
            </div>
            <div className="h-80 bg-gray-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    )
  }
  
  const tabs = [
    { id: 'overview', name: 'Overview', icon: ChartBarIcon },
    { id: 'manage', name: 'Manage Billing', icon: CreditCardIcon },
    { id: 'history', name: 'Billing History', icon: CalendarDaysIcon }
  ]
  
  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Billing & Usage
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Manage your subscription, monitor usage, and view billing history
        </p>
      </div>
      
      {/* Trial Status Alert */}
      {trialStatus && (
        <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center">
            <InformationCircleIcon className="h-5 w-5 text-blue-500 mr-3" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Free Trial Active
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {trialStatus.daysLeft > 0 
                  ? `Your free trial ends in ${trialStatus.daysLeft} days (${trialStatus.trialEnd})`
                  : 'Your free trial has ended'
                }
              </p>
            </div>
            {trialStatus.daysLeft <= 3 && (
              <button
                onClick={() => setActiveTab('overview')}
                className="ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-800 dark:text-blue-200 dark:hover:bg-blue-700 transition-colors"
              >
                Choose Plan
              </button>
            )}
          </div>
        </div>
      )}
      
      {/* Usage Alerts */}
      {usageAlerts.length > 0 && (
        <div className="mb-6 space-y-3">
          {usageAlerts.map((alert, index) => (
            <div key={index} className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 mr-3" />
                  <div>
                    <h3 className="text-sm font-medium text-amber-900 dark:text-amber-100">
                      {alert.title}
                    </h3>
                    <p className="text-sm text-amber-700 dark:text-amber-300">
                      {alert.message}
                    </p>
                  </div>
                </div>
                {canUpgrade() && (
                  <button
                    onClick={() => setActiveTab('overview')}
                    className="ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded text-amber-700 bg-amber-100 hover:bg-amber-200 dark:bg-amber-800 dark:text-amber-200 dark:hover:bg-amber-700 transition-colors"
                  >
                    <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
                    Upgrade
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Tabs Navigation */}
      <div className="mb-6">
        <nav className="flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <Icon className="h-5 w-5 mr-2" />
                {tab.name}
              </button>
            )
          })}
        </nav>
      </div>
      
      {/* Tab Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {activeTab === 'overview' && (
          <>
            {/* Main Content Area */}
            <div className="lg:col-span-2">
              {/* Current Plan Summary */}
              {plan && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Current Plan
                    </h3>
                    {billingInfo?.subscription_status === 'active' && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                        <CheckCircleIconSolid className="h-3 w-3 mr-1" />
                        Active
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-4 mb-6">
                    <div className="bg-blue-100 dark:bg-blue-900 p-3 rounded-lg">
                      <ChartBarIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-gray-900 dark:text-white">
                        {plan.display_name || plan.plan_name}
                      </h4>
                      <p className="text-gray-600 dark:text-gray-400">
                        {billingInfo?.amount 
                          ? `${formatAmount(billingInfo.amount, billingInfo.currency)} / ${billingInfo.interval || 'month'}`
                          : 'Free plan'
                        }
                      </p>
                    </div>
                  </div>
                  
                  {/* Plan Features */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {plan.max_posts_per_day || 0}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Posts per day
                      </div>
                    </div>
                    
                    <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {plan.image_generation_limit || 0}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Images per month
                      </div>
                    </div>
                    
                    <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {plan.max_social_profiles || 1}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Social profiles
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Usage Monitoring */}
              {limits && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                    Usage Overview
                  </h3>
                  
                  <div className="space-y-6">
                    <EnhancedUsageIndicator
                      limitType="posts"
                      showUpgradePrompt={true}
                      showPercentage={true}
                      showRemaining={true}
                    />
                    
                    <EnhancedUsageIndicator
                      limitType="images"
                      showUpgradePrompt={true}
                      showPercentage={true}
                      showRemaining={true}
                    />
                    
                    <EnhancedUsageIndicator
                      limitType="social_profiles"
                      showUpgradePrompt={true}
                      showPercentage={true}
                      showRemaining={true}
                    />
                  </div>
                </div>
              )}
            </div>
            
            {/* Sidebar */}
            <div>
              {/* Upcoming Invoice */}
              {upcomingInvoice && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                    <BanknotesIcon className="h-5 w-5 mr-2" />
                    Next Invoice
                  </h3>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Amount</span>
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {formatAmount(upcomingInvoice.amount_due, upcomingInvoice.currency)}
                      </span>
                    </div>
                    
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Due Date</span>
                      <span className="text-gray-900 dark:text-white">
                        {new Date(upcomingInvoice.next_payment_attempt).toLocaleDateString()}
                      </span>
                    </div>
                    
                    <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Covers {new Date(upcomingInvoice.period_start).toLocaleDateString()} - {new Date(upcomingInvoice.period_end).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Security Badge */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <div className="text-center">
                  <div className="bg-green-100 dark:bg-green-900 p-3 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                    <ShieldCheckIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
                  </div>
                  
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                    Secure Billing
                  </h3>
                  
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Your payment information is securely processed by Stripe. 
                    We never store your credit card details.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
        
        {activeTab === 'manage' && (
          <div className="lg:col-span-3">
            <StripePortalManager billingInfo={billingInfo} />
          </div>
        )}
        
        {activeTab === 'history' && (
          <div className="lg:col-span-3">
            <BillingHistory />
          </div>
        )}
      </div>
    </div>
  )
}

export default BillingOverview