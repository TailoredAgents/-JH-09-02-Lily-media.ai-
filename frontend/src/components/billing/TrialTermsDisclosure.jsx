import React, { useState, useEffect } from 'react'
import FocusTrap from '../accessibility/FocusTrap'
import ScreenReaderOnly, { LiveRegion } from '../accessibility/ScreenReaderOnly'
import { useAccessibleId, useAriaDescribedBy } from '../../hooks/useAccessibleId'
import {
  InformationCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CreditCardIcon,
  XMarkIcon,
  CalendarDaysIcon,
  BanknotesIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline'

/**
 * P1-10b: FTC-Compliant Trial Terms Disclosure Component
 * P1-10c: WCAG 2.1 AA Accessibility Enhanced
 * 
 * Implements comprehensive trial and renewal term disclosures per FTC Click-to-Cancel Rule
 * and consumer protection regulations effective July 14, 2025
 * 
 * FTC Requirements:
 * - Clear disclosure of trial duration and automatic conversion
 * - Explicit billing date and amount disclosure
 * - Cancellation deadline and mechanism information
 * - No misrepresentations of material facts
 * - Adjacent placement to consent mechanism
 * 
 * WCAG 2.1 AA Requirements:
 * - 2.1.1 Keyboard accessible
 * - 2.4.3 Focus Order and 2.4.7 Focus Visible
 * - 1.3.1 Info and Relationships (proper ARIA)
 * - 3.3.2 Labels or Instructions
 * - 4.1.2 Name, Role, Value
 */
const TrialTermsDisclosure = ({
  planName = 'Pro',
  trialDays = 14,
  monthlyPrice = 99,
  annualPrice = 79,
  isAnnualBilling = false,
  isVisible = true,
  onAccept = () => {},
  onDecline = () => {},
  showModal = false,
  onCloseModal = () => {},
  requireExplicitConsent = false
}) => {
  const [hasReadTerms, setHasReadTerms] = useState(false)
  const [scrolledToBottom, setScrolledToBottom] = useState(false)
  const [currentDate] = useState(new Date())
  const [liveRegionMessage, setLiveRegionMessage] = useState('')
  
  // P1-10c: Generate accessible IDs for ARIA relationships
  const ids = useAccessibleId('trial-terms-disclosure')
  
  // Calculate important dates
  const trialEndDate = new Date(currentDate)
  trialEndDate.setDate(trialEndDate.getDate() + trialDays)
  
  const firstBillingDate = new Date(trialEndDate)
  firstBillingDate.setDate(firstBillingDate.getDate() + 1)
  
  const cancellationDeadline = new Date(trialEndDate)
  cancellationDeadline.setHours(23, 59, 59, 999) // End of day
  
  const currentPrice = isAnnualBilling ? annualPrice : monthlyPrice
  const billingInterval = isAnnualBilling ? 'annually' : 'monthly'
  const nextBillingDate = isAnnualBilling 
    ? new Date(firstBillingDate.getFullYear() + 1, firstBillingDate.getMonth(), firstBillingDate.getDate())
    : new Date(firstBillingDate.getFullYear(), firstBillingDate.getMonth() + 1, firstBillingDate.getDate())
  
  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }
  
  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short'
    })
  }
  
  // P1-10c: Enhanced scroll handling with accessibility announcements
  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10
    if (isAtBottom && !scrolledToBottom) {
      setScrolledToBottom(true)
      setLiveRegionMessage('You have reached the end of the terms and conditions')
    }
  }
  
  // P1-10c: Enhanced accept handler with accessibility feedback
  const handleAccept = () => {
    setHasReadTerms(true)
    setLiveRegionMessage('Terms and conditions accepted. Proceeding with subscription.')
    onAccept({
      acknowledged: true,
      trialEndDate: trialEndDate.toISOString(),
      firstBillingDate: firstBillingDate.toISOString(),
      billingAmount: currentPrice,
      billingInterval,
      cancellationDeadline: cancellationDeadline.toISOString()
    })
  }
  
  // P1-10c: Handle escape key for modal closure
  const handleEscape = () => {
    setLiveRegionMessage('Terms dialog closed without accepting.')
    onCloseModal()
  }
  
  if (!isVisible) return null
  
  const DisclosureContent = () => (
    <div className="space-y-6" role="main">
      {/* Skip to Action Buttons Link - WCAG 2.4.1 Bypass Blocks */}
      <div className="sr-only focus-within:not-sr-only">
        <a 
          href={`#${ids.relatedId('action-buttons')}`}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          onFocus={(e) => e.target.scrollIntoView({ behavior: 'smooth', block: 'center' })}
        >
          Skip to action buttons
        </a>
      </div>
      {/* Primary Disclosure - FTC Required Material Terms */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
        <div className="flex items-start space-x-3">
          <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-bold text-yellow-900 dark:text-yellow-100 mb-3">
              IMPORTANT BILLING INFORMATION
            </h3>
            
            <div className="space-y-4">
              {/* Auto-Renewal Notice */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-yellow-200 dark:border-yellow-700">
                <div className="flex items-center space-x-2 mb-2">
                  <CreditCardIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                  <span className="font-semibold text-gray-900 dark:text-white">
                    Automatic Renewal Subscription
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <strong>Your subscription will automatically renew and you will be charged ${currentPrice} {billingInterval}</strong> 
                  {' '}unless you cancel before the trial ends. After your free trial, charges will continue every{' '}
                  {isAnnualBilling ? 'year' : 'month'} until you cancel.
                </p>
              </div>
              
              {/* Trial Period */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-yellow-200 dark:border-yellow-700">
                <div className="flex items-center space-x-2 mb-2">
                  <ClockIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                  <span className="font-semibold text-gray-900 dark:text-white">
                    Free Trial Period
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  Your <strong>{trialDays}-day free trial</strong> begins today and ends on{' '}
                  <strong>{formatDate(trialEndDate)}</strong> at <strong>{formatTime(cancellationDeadline)}</strong>.
                </p>
              </div>
              
              {/* First Billing Date */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-yellow-200 dark:border-yellow-700">
                <div className="flex items-center space-x-2 mb-2">
                  <BanknotesIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                  <span className="font-semibold text-gray-900 dark:text-white">
                    First Billing Date
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  You will be charged <strong>${currentPrice}</strong> on{' '}
                  <strong>{formatDate(firstBillingDate)}</strong> and then every{' '}
                  {isAnnualBilling ? 'year' : 'month'} thereafter on the same date.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Cancellation Information */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
        <div className="flex items-start space-x-3">
          <InformationCircleIcon className="h-6 w-6 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
              How to Cancel Your Subscription
            </h3>
            
            <div className="space-y-4">
              {/* Cancellation Deadline */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-blue-200 dark:border-blue-700">
                <div className="flex items-center space-x-2 mb-2">
                  <CalendarDaysIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  <span className="font-semibold text-gray-900 dark:text-white">
                    Cancellation Deadline
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <strong>You must cancel by {formatDate(cancellationDeadline)} at {formatTime(cancellationDeadline)}</strong>
                  {' '}to avoid being charged. Cancellations after this deadline will take effect at the end of the current billing period.
                </p>
              </div>
              
              {/* How to Cancel */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-blue-200 dark:border-blue-700">
                <div className="flex items-center space-x-2 mb-3">
                  <XMarkIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  <span className="font-semibold text-gray-900 dark:text-white">
                    Cancellation Methods
                  </span>
                </div>
                <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                  <div className="flex items-center space-x-2">
                    <ArrowRightIcon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span>Go to Settings → Billing → Manage Subscription → Cancel</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <ArrowRightIcon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span>Use the "Cancel Subscription" button in your billing portal</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <ArrowRightIcon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span>Contact support at support@lily-ai.com</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Billing Schedule */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <CalendarDaysIcon className="h-5 w-5 mr-2" />
          Billing Schedule
        </h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg border">
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Today</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Trial starts</div>
            </div>
            <div className="text-green-600 dark:text-green-400 font-medium">Free</div>
          </div>
          
          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg border">
            <div>
              <div className="font-medium text-gray-900 dark:text-white">
                {formatDate(trialEndDate)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Trial ends</div>
            </div>
            <div className="text-yellow-600 dark:text-yellow-400 font-medium">Last chance to cancel</div>
          </div>
          
          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg border">
            <div>
              <div className="font-medium text-gray-900 dark:text-white">
                {formatDate(firstBillingDate)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">First billing date</div>
            </div>
            <div className="text-red-600 dark:text-red-400 font-medium">${currentPrice}</div>
          </div>
          
          <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-700 rounded-lg border">
            <div>
              <div className="font-medium text-gray-900 dark:text-white">
                {formatDate(nextBillingDate)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Next billing date</div>
            </div>
            <div className="text-red-600 dark:text-red-400 font-medium">${currentPrice}</div>
          </div>
        </div>
      </div>
      
      {/* Legal Compliance Notice */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <ShieldCheckIcon className="h-5 w-5 mr-2" />
          Consumer Rights & Legal Information
        </h3>
        
        <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
          <div className="flex items-start space-x-2">
            <CheckCircleIcon className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <span>
              This subscription complies with FTC Click-to-Cancel Rule and consumer protection regulations
            </span>
          </div>
          <div className="flex items-start space-x-2">
            <CheckCircleIcon className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <span>
              You have the right to cancel at any time through multiple accessible methods
            </span>
          </div>
          <div className="flex items-start space-x-2">
            <CheckCircleIcon className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <span>
              No cancellation fees or penalties apply when you cancel your subscription
            </span>
          </div>
          <div className="flex items-start space-x-2">
            <DocumentTextIcon className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <span>
              Full terms available in our{' '}
              <a href="/terms" className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
                Terms of Service
              </a>
              {' '}and{' '}
              <a href="/privacy" className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
                Privacy Policy
              </a>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
  
  if (showModal) {
    return (
      <>
        {/* P1-10c: WCAG 2.1 AA Accessible Modal with Focus Trap */}
        <div className="fixed inset-0 z-50 overflow-y-auto" role="presentation">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Backdrop */}
            <div 
              className="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity" 
              onClick={onCloseModal}
              aria-hidden="true"
            />
            
            {/* Modal Content with Focus Trap */}
            <FocusTrap
              active={showModal}
              onEscape={handleEscape}
              className="inline-block align-bottom bg-white dark:bg-gray-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full"
              role="dialog"
              ariaLabelledBy={ids.modalTitleId}
              ariaDescribedBy={ids.modalDescId}
            >
              <div className="bg-white dark:bg-gray-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="w-full">
                    {/* Modal Header */}
                    <div className="flex items-center justify-between mb-4">
                      <h1 
                        id={ids.modalTitleId}
                        className="text-lg font-semibold text-gray-900 dark:text-white"
                      >
                        Trial and Billing Terms
                      </h1>
                      <button
                        onClick={onCloseModal}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded"
                        aria-label="Close terms and conditions dialog"
                      >
                        <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                      </button>
                    </div>
                    
                    {/* Screen Reader Description */}
                    <ScreenReaderOnly id={ids.modalDescId}>
                      Modal dialog containing important trial and billing terms. Review all information before accepting or declining.
                    </ScreenReaderOnly>
                  
                    {/* Scrollable Content Area */}
                    <div 
                      className="max-h-96 overflow-y-auto pr-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded"
                      onScroll={handleScroll}
                      tabIndex={0}
                      role="region"
                      aria-label="Scrollable terms and conditions content"
                      aria-describedby={ids.relatedId('scroll-instructions')}
                    >
                      <ScreenReaderOnly id={ids.relatedId('scroll-instructions')}>
                        Use arrow keys or page up/down to scroll through the terms and conditions. Press Tab to move to the next interactive element.
                      </ScreenReaderOnly>
                      <DisclosureContent />
                    </div>
                  
                    {/* Consent Checkbox - WCAG 2.1 AA Compliant */}
                    {requireExplicitConsent && (
                      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <fieldset>
                          <legend className="sr-only">Terms and Conditions Consent</legend>
                          <div className="flex items-start space-x-3">
                            <input
                              id={ids.relatedId('consent-checkbox')}
                              type="checkbox"
                              checked={hasReadTerms}
                              onChange={(e) => {
                                setHasReadTerms(e.target.checked)
                                setLiveRegionMessage(
                                  e.target.checked 
                                    ? 'Terms accepted. You may now proceed with subscription.'
                                    : 'Terms consent removed.'
                                )
                              }}
                              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 focus:ring-2 border-gray-300 rounded"
                              aria-describedby={ids.relatedId('consent-description')}
                              required
                            />
                            <label 
                              htmlFor={ids.relatedId('consent-checkbox')}
                              className="text-sm text-gray-900 dark:text-white cursor-pointer"
                            >
                              I have read and understand the trial and billing terms above. I acknowledge that my subscription will automatically renew and I will be charged ${currentPrice} {billingInterval} starting {formatDate(firstBillingDate)} unless I cancel by {formatDate(cancellationDeadline)}.
                            </label>
                          </div>
                          <div id={ids.relatedId('consent-description')} className="sr-only">
                            Required checkbox to acknowledge and accept the trial and billing terms before proceeding with subscription.
                          </div>
                        </fieldset>
                      </div>
                    )}
                  
                    {/* Action Buttons - WCAG 2.1 AA Compliant */}
                    <div 
                      id={ids.relatedId('action-buttons')}
                      className="mt-6 flex justify-end space-x-3" 
                      role="group" 
                      aria-label="Terms and conditions actions"
                    >
                      <button
                        onClick={onDecline}
                        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                        aria-describedby={ids.relatedId('decline-description')}
                      >
                        Decline
                      </button>
                      <ScreenReaderOnly id={ids.relatedId('decline-description')}>
                        Decline the terms and conditions and close this dialog without subscribing
                      </ScreenReaderOnly>
                      
                      <button
                        onClick={handleAccept}
                        disabled={requireExplicitConsent && !hasReadTerms}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        aria-describedby={ids.relatedId('accept-description')}
                      >
                        I Understand and Accept
                      </button>
                      <ScreenReaderOnly id={ids.relatedId('accept-description')}>
                        {requireExplicitConsent && !hasReadTerms 
                          ? 'Accept button disabled. You must check the consent checkbox first.'
                          : 'Accept the terms and conditions and proceed with subscription'
                        }
                      </ScreenReaderOnly>
                    </div>
                  </div>
                </div>
              </FocusTrap>
            </div>
          </div>
        </div>
        
        {/* Live Region for Screen Reader Announcements */}
        <LiveRegion level="polite" atomic={false}>
          {liveRegionMessage}
        </LiveRegion>
      </>
    )
  }
  
  return (
    <div className="w-full">
      <DisclosureContent />
    </div>
  )
}

export default TrialTermsDisclosure