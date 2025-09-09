import React, { useState } from 'react'
import { 
  XMarkIcon, 
  ExclamationTriangleIcon,
  HeartIcon,
  CalendarIcon,
  ShieldCheckIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'

/**
 * P1-10a: Consumer Protection Cancellation Modal
 * 
 * Provides FTC-compliant pre-cancellation information and options
 * before redirecting users to Stripe Customer Portal for final cancellation
 */
const CancellationModal = ({ 
  isOpen, 
  onClose, 
  onProceedToPortal,
  planName = 'Pro',
  nextBillingDate,
  monthlyAmount,
  remainingDays = 0
}) => {
  const [selectedReason, setSelectedReason] = useState('')
  const [feedback, setFeedback] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)

  if (!isOpen) return null

  const cancellationReasons = [
    { value: 'cost', label: 'Too expensive', icon: '💰' },
    { value: 'features', label: 'Missing features I need', icon: '🔧' },
    { value: 'complexity', label: 'Too complicated to use', icon: '🤔' },
    { value: 'alternatives', label: 'Found a better alternative', icon: '🔄' },
    { value: 'usage', label: 'Not using it enough', icon: '📊' },
    { value: 'temporary', label: 'Temporary pause', icon: '⏸️' },
    { value: 'other', label: 'Other reason', icon: '📝' }
  ]

  const handleReasonSelect = (reason) => {
    setSelectedReason(reason)
    if (reason === 'other' || reason === 'features' || reason === 'complexity') {
      setShowFeedback(true)
    }
  }

  const handleProceedToPortal = () => {
    // Pass feedback data to parent component for API submission
    onProceedToPortal({
      reason: selectedReason,
      feedback: feedback,
      timestamp: new Date().toISOString()
    })
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose} />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:p-6">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 pb-4">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-6 w-6 text-amber-500 mr-2" />
              <h3 className="text-lg font-semibold text-gray-900">
                Before you cancel...
              </h3>
            </div>
            <button
              onClick={onClose}
              className="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          <div className="mt-6">
            {/* Consumer Protection Notice */}
            <div className="mb-6 rounded-lg bg-blue-50 border border-blue-200 p-4">
              <div className="flex items-start">
                <ShieldCheckIcon className="h-5 w-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
                <div className="text-sm text-blue-800">
                  <h4 className="font-medium mb-2">Your Consumer Rights</h4>
                  <ul className="space-y-1 text-sm">
                    <li>• You can cancel anytime with no penalties</li>
                    <li>• Cancellation takes effect at the end of your current billing period</li>
                    <li>• You'll keep access until {nextBillingDate}</li>
                    <li>• Your data is safely retained for 30 days after cancellation</li>
                    <li>• You can easily reactivate your account anytime</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* What You'll Lose */}
            <div className="mb-6">
              <h4 className="font-medium text-gray-900 mb-3">What happens when you cancel:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <h5 className="font-medium text-red-800 mb-2">You'll lose access to:</h5>
                  <ul className="text-red-700 space-y-1">
                    <li>• Advanced AI features</li>
                    <li>• Premium templates</li>
                    <li>• Priority support</li>
                    <li>• Advanced analytics</li>
                  </ul>
                </div>
                <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                  <h5 className="font-medium text-green-800 mb-2">You'll keep:</h5>
                  <ul className="text-green-700 space-y-1">
                    <li>• Your account and data</li>
                    <li>• Basic free features</li>
                    <li>• Ability to reactivate</li>
                    <li>• Content history</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Alternative Options */}
            <div className="mb-6 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 p-4">
              <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                <HeartIcon className="h-5 w-5 text-purple-600 mr-2" />
                Before you go, consider these options:
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <button className="text-left p-3 rounded-lg bg-white border border-purple-200 hover:border-purple-300 transition-colors">
                  <div className="font-medium text-purple-700">💬 Talk to Support</div>
                  <div className="text-gray-600 mt-1">Get help with any issues</div>
                </button>
                <button className="text-left p-3 rounded-lg bg-white border border-purple-200 hover:border-purple-300 transition-colors">
                  <div className="font-medium text-purple-700">⏸️ Pause Billing</div>
                  <div className="text-gray-600 mt-1">Temporarily pause payments</div>
                </button>
                <button className="text-left p-3 rounded-lg bg-white border border-purple-200 hover:border-purple-300 transition-colors">
                  <div className="font-medium text-purple-700">📉 Downgrade Plan</div>
                  <div className="text-gray-600 mt-1">Switch to a lower plan</div>
                </button>
              </div>
            </div>

            {/* Cancellation Reason */}
            <div className="mb-6">
              <h4 className="font-medium text-gray-900 mb-3">
                Help us improve - Why are you cancelling? (Optional)
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {cancellationReasons.map((reason) => (
                  <button
                    key={reason.value}
                    onClick={() => handleReasonSelect(reason.value)}
                    className={`text-left p-3 rounded-lg border transition-colors ${
                      selectedReason === reason.value
                        ? 'border-indigo-300 bg-indigo-50 text-indigo-700'
                        : 'border-gray-200 bg-gray-50 hover:border-gray-300 text-gray-700'
                    }`}
                  >
                    <div className="flex items-center">
                      <span className="mr-2">{reason.icon}</span>
                      <span className="text-sm font-medium">{reason.label}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Feedback Section */}
            {showFeedback && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tell us more (This helps us improve):
                </label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  rows={3}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  placeholder="What could we do better?"
                />
              </div>
            )}

            {/* Billing Information */}
            <div className="mb-6 rounded-lg bg-gray-50 border border-gray-200 p-4">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center">
                  <CalendarIcon className="h-4 w-4 text-gray-500 mr-2" />
                  <span className="text-gray-600">Current plan:</span>
                </div>
                <span className="font-medium text-gray-900">{planName} - ${monthlyAmount}/month</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-600">Access until:</span>
                <span className="font-medium text-gray-900">{nextBillingDate}</span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-600">Remaining days:</span>
                <span className="font-medium text-gray-900">{remainingDays} days</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <button
              onClick={onClose}
              className="flex-1 inline-flex justify-center items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Keep My Subscription
            </button>
            <button
              onClick={handleProceedToPortal}
              className="flex-1 inline-flex justify-center items-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              Proceed to Cancel
            </button>
          </div>

          {/* Fine Print */}
          <div className="mt-4 text-xs text-gray-500 text-center">
            <p>
              Secure cancellation powered by Stripe. Your billing information is protected by bank-level encryption.
              <br />
              Questions? Contact support at support@lily-ai.com or chat with us.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CancellationModal