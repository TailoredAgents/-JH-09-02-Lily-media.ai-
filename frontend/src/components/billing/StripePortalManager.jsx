import React, { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { usePlan } from '../../contexts/PlanContext'
import { useNotifications } from '../../hooks/useNotifications'
import CancellationModal from './CancellationModal'
import api from '../../services/api'
import {
  CreditCardIcon,
  ArrowTopRightOnSquareIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  CalendarIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline'

/**
 * Stripe Customer Portal Manager
 * 
 * Provides comprehensive billing management through Stripe Customer Portal
 * with enhanced security and user experience features
 */
const StripePortalManager = ({ billingInfo = null }) => {
  const { user } = useAuth()
  const { plan, refreshPlan } = usePlan()
  const { showSuccess, showError, showInfo } = useNotifications()
  
  const [portalLoading, setPortalLoading] = useState(false)
  const [cancelLoading, setCancelLoading] = useState(false)
  const [updatePaymentLoading, setUpdatePaymentLoading] = useState(false)
  const [showCancellationModal, setShowCancellationModal] = useState(false)
  
  const handleManageSubscription = async () => {
    if (portalLoading) return
    
    setPortalLoading(true)
    try {
      const response = await api.request('/api/billing/customer-portal', {
        method: 'POST',
        body: {
          return_url: window.location.href,
          // Specify which features to enable in the portal
          configuration: {
            business_profile: {
              privacy_policy_url: `${window.location.origin}/privacy`,
              terms_of_service_url: `${window.location.origin}/terms`
            },
            features: {
              payment_method_update: { enabled: true },
              invoice_history: { enabled: true },
              subscription_update: {
                enabled: true,
                proration_behavior: 'create_prorations'
              },
              subscription_cancel: {
                enabled: true,
                mode: 'at_period_end',
                cancellation_reason: {
                  enabled: true,
                  options: [
                    'too_expensive',
                    'missing_features', 
                    'switched_service',
                    'unused',
                    'other'
                  ]
                }
              }
            }
          }
        }
      })
      
      // Track portal access for analytics
      if (window.gtag) {
        window.gtag('event', 'billing_portal_access', {
          event_category: 'billing',
          event_label: plan?.plan_name || 'unknown'
        })
      }
      
      // Open in same tab for better security
      window.location.href = response.portal_url
      
    } catch (error) {
      console.error('Failed to open customer portal:', error)
      showError(
        error.response?.data?.detail || 
        'Failed to open subscription management. Please try again or contact support.'
      )
    } finally {
      setPortalLoading(false)
    }
  }
  
  // P1-10a: Enhanced cancellation with consumer protection modal
  const handleCancelSubscription = () => {
    setShowCancellationModal(true)
  }

  const handleProceedToPortal = async (cancellationData) => {
    setShowCancellationModal(false)
    
    // Submit cancellation feedback to API before redirecting
    try {
      if (cancellationData.reason) {
        await api.request('/api/billing/cancellation-feedback', {
          method: 'POST',
          body: {
            reason: cancellationData.reason,
            feedback: cancellationData.feedback,
            timestamp: cancellationData.timestamp
          },
        })
      }
    } catch (error) {
      console.warn('Failed to submit cancellation feedback:', error)
      // Don't block the user from cancelling if feedback submission fails
    }

    // Proceed to Stripe Customer Portal for final cancellation
    handleManageSubscription()
  }
  
  const handleUpdatePaymentMethod = async () => {
    if (updatePaymentLoading) return
    
    setUpdatePaymentLoading(true)
    try {
      const response = await api.request('/api/billing/customer-portal', {
        method: 'POST',
        body: {
          return_url: window.location.href,
          flow_data: {
            type: 'payment_method_update'
          }
        }
      })
      
      window.location.href = response.portal_url
      
    } catch (error) {
      console.error('Failed to open payment method update:', error)
      showError('Failed to open payment method update')
    } finally {
      setUpdatePaymentLoading(false)
    }
  }
  
  // P1-10a: Direct cancellation function (legacy - replaced by modal flow)
  const handleDirectCancelSubscription = async () => {
    if (cancelLoading) return
    
    // Show confirmation dialog
    const confirmed = window.confirm(
      'Are you sure you want to cancel your subscription? Your access will continue until the end of your current billing period.'
    )
    
    if (!confirmed) return
    
    setCancelLoading(true)
    try {
      await api.cancelSubscription()
      
      showInfo(
        'Your subscription has been scheduled for cancellation at the end of your current billing period. You can reactivate it anytime before then.'
      )
      
      // Refresh plan data to reflect cancellation
      await refreshPlan()
      
    } catch (error) {
      console.error('Failed to cancel subscription:', error)
      showError(
        error.response?.data?.detail || 
        'Failed to cancel subscription. Please try again or use the billing portal.'
      )
    } finally {
      setCancelLoading(false)
    }
  }
  
  const getSubscriptionStatus = () => {
    if (!billingInfo) return null
    
    const status = billingInfo.subscription_status
    const cancelAtPeriodEnd = billingInfo.cancel_at_period_end
    
    if (cancelAtPeriodEnd) {
      return {
        text: 'Cancels at period end',
        color: 'text-yellow-700 bg-yellow-100 border-yellow-200',
        icon: ExclamationTriangleIcon
      }
    }
    
    switch (status) {
      case 'active':
        return {
          text: 'Active',
          color: 'text-green-700 bg-green-100 border-green-200',
          icon: ShieldCheckIcon
        }
      case 'trialing':
        return {
          text: 'Free Trial',
          color: 'text-blue-700 bg-blue-100 border-blue-200',
          icon: InformationCircleIcon
        }
      case 'past_due':
        return {
          text: 'Past Due',
          color: 'text-red-700 bg-red-100 border-red-200',
          icon: ExclamationTriangleIcon
        }
      case 'canceled':
        return {
          text: 'Canceled',
          color: 'text-gray-700 bg-gray-100 border-gray-200',
          icon: ExclamationTriangleIcon
        }
      default:
        return null
    }
  }
  
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }
  
  const statusInfo = getSubscriptionStatus()
  const hasActiveSubscription = billingInfo?.stripe_customer_id && 
    ['active', 'trialing', 'past_due'].includes(billingInfo?.subscription_status)
  
  return (
    <div className="space-y-6">
      {/* Subscription Status Card */}
      {billingInfo && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Subscription Details
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {statusInfo && (
                  <div className="flex items-center space-x-3">
                    <statusInfo.icon className="h-5 w-5 text-gray-500" />
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">Status</div>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusInfo.color}`}>
                        {statusInfo.text}
                      </span>
                    </div>
                  </div>
                )}
                
                {billingInfo.current_period_end && (
                  <div className="flex items-center space-x-3">
                    <CalendarIcon className="h-5 w-5 text-gray-500" />
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {billingInfo.cancel_at_period_end ? 'Cancels on' : 'Renews on'}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(billingInfo.current_period_end)}
                      </div>
                    </div>
                  </div>
                )}
                
                {billingInfo.amount && (
                  <div className="flex items-center space-x-3">
                    <CurrencyDollarIcon className="h-5 w-5 text-gray-500" />
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {billingInfo.cancel_at_period_end ? 'Final charge' : 'Next charge'}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        ${(billingInfo.amount / 100).toFixed(2)} {billingInfo.currency?.toUpperCase()}
                      </div>
                    </div>
                  </div>
                )}
                
                {billingInfo.payment_method && (
                  <div className="flex items-center space-x-3">
                    <CreditCardIcon className="h-5 w-5 text-gray-500" />
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">Payment Method</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {billingInfo.payment_method.brand?.toUpperCase()} •••• {billingInfo.payment_method.last4}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Management Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Billing Management
        </h3>
        
        <div className="space-y-4">
          {/* Primary Portal Access */}
          <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 dark:bg-blue-900 p-2 rounded-lg">
                <ArrowTopRightOnSquareIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <div className="font-medium text-blue-900 dark:text-blue-100">
                  Stripe Customer Portal
                </div>
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  Manage your subscription, payment methods, and billing history
                </div>
              </div>
            </div>
            <button
              onClick={handleManageSubscription}
              disabled={portalLoading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {portalLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Opening...
                </>
              ) : (
                <>
                  <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-2" />
                  Open Portal
                </>
              )}
            </button>
          </div>
          
          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {hasActiveSubscription && (
              <button
                onClick={handleUpdatePaymentMethod}
                disabled={updatePaymentLoading}
                className="flex items-center justify-center p-4 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
              >
                <CreditCardIcon className="h-5 w-5 mr-3 text-gray-500" />
                <div className="text-left">
                  <div className="font-medium text-gray-900 dark:text-white">
                    Update Payment Method
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Change your billing card
                  </div>
                </div>
              </button>
            )}
            
            {hasActiveSubscription && !billingInfo?.cancel_at_period_end && (
              <button
                onClick={handleCancelSubscription}
                disabled={cancelLoading}
                className="flex items-center justify-center p-4 border border-red-300 dark:border-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 transition-colors"
              >
                <ExclamationTriangleIcon className="h-5 w-5 mr-3 text-red-500" />
                <div className="text-left">
                  <div className="font-medium text-red-900 dark:text-red-100">
                    Cancel Subscription
                  </div>
                  <div className="text-sm text-red-700 dark:text-red-300">
                    Cancel at period end
                  </div>
                </div>
              </button>
            )}
          </div>
        </div>
        
        {/* Security Notice */}
        <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="flex items-start space-x-3">
            <ShieldCheckIcon className="h-5 w-5 text-gray-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                Secure Billing Management
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                All billing operations are processed securely through Stripe. Your payment information 
                is never stored on our servers. The customer portal provides secure access to update 
                payment methods, view invoices, and manage your subscription.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* P1-10a: Consumer Protection Cancellation Modal */}
      <CancellationModal
        isOpen={showCancellationModal}
        onClose={() => setShowCancellationModal(false)}
        onProceedToPortal={handleProceedToPortal}
        planName={plan?.plan_name || 'Pro'}
        nextBillingDate={billingInfo?.current_period_end ? 
          formatDate(billingInfo.current_period_end) : 'N/A'}
        monthlyAmount={billingInfo?.amount ? 
          (billingInfo.amount / 100).toFixed(2) : '0.00'}
        remainingDays={billingInfo?.current_period_end ? 
          Math.max(0, Math.ceil((new Date(billingInfo.current_period_end) - new Date()) / (1000 * 60 * 60 * 24))) : 0}
      />
    </div>
  )
}

export default StripePortalManager