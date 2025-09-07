import React, { useState, useEffect } from 'react'
import { usePlanConditionals } from '../../hooks/usePlanConditionals'
import { useNotifications } from '../../hooks/useNotifications'
import {
  ExclamationTriangleIcon,
  LockClosedIcon,
  ArrowUpIcon,
  InformationCircleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'

/**
 * Action Quota Guard Component
 *
 * Provides contextual quota checking and upgrade flows
 * for specific user actions before they are performed
 */
const ActionQuotaGuard = ({
  action, // 'create_post', 'generate_image', 'add_profile', etc.
  limitType, // 'posts', 'images', 'social_profiles', etc.
  children,
  showWarningThreshold = 80, // Show warning at 80% usage
  preventActionAtLimit = true,
  customUpgradeMessage = null,
  onActionBlocked = null,
  className = '',
}) => {
  const {
    canPerformAction,
    getUsagePercentage,
    getLimitStatus,
    getUpgradeMessage,
    canUpgrade,
  } = usePlanConditionals()

  const { showInfo, showWarning } = useNotifications()
  const [lastChecked, setLastChecked] = useState(Date.now())

  const limitStatus = getLimitStatus(limitType)
  const usage = getUsagePercentage(limitType)
  const canPerform = canPerformAction(limitType, action)

  // Check quota status when component mounts or action changes
  useEffect(() => {
    setLastChecked(Date.now())

    // Show contextual notifications based on usage
    if (usage >= 90 && canPerform) {
      showWarning(
        `You're at ${Math.round(usage)}% of your ${limitType.replace('_', ' ')} limit`
      )
    } else if (usage >= showWarningThreshold && usage < 90) {
      showInfo(
        `${limitStatus.remaining} ${limitType.replace('_', ' ')} remaining`
      )
    }
  }, [
    action,
    limitType,
    usage,
    canPerform,
    showWarningThreshold,
    limitStatus.remaining,
    showInfo,
    showWarning,
  ])

  const handleActionAttempt = (event) => {
    if (!canPerform && preventActionAtLimit) {
      event.preventDefault()
      event.stopPropagation()

      if (onActionBlocked) {
        onActionBlocked({
          action,
          limitType,
          reason: limitStatus.status,
          upgradeMessage: customUpgradeMessage || getUpgradeMessage(limitType),
        })
      }

      return false
    }
    return true
  }

  const handleUpgradeClick = (event) => {
    event.preventDefault()
    event.stopPropagation()
    window.location.href = '/billing'
  }

  // Helper to get status styling
  const getStatusStyling = () => {
    if (!canPerform) {
      return {
        containerClass:
          'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800',
        textClass: 'text-red-700 dark:text-red-300',
        iconClass: 'text-red-500',
        icon: LockClosedIcon,
      }
    } else if (usage >= 90) {
      return {
        containerClass:
          'border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800',
        textClass: 'text-amber-700 dark:text-amber-300',
        iconClass: 'text-amber-500',
        icon: ExclamationTriangleIcon,
      }
    } else if (usage >= showWarningThreshold) {
      return {
        containerClass:
          'border-blue-300 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-800',
        textClass: 'text-blue-700 dark:text-blue-300',
        iconClass: 'text-blue-500',
        icon: InformationCircleIcon,
      }
    }

    return {
      containerClass:
        'border-green-300 bg-green-50 dark:bg-green-900/20 dark:border-green-800',
      textClass: 'text-green-700 dark:text-green-300',
      iconClass: 'text-green-500',
      icon: CheckCircleIcon,
    }
  }

  const styling = getStatusStyling()
  const StatusIcon = styling.icon

  // If action can be performed without issues, just render children
  if (canPerform && usage < showWarningThreshold) {
    return (
      <div className={className} onClick={handleActionAttempt}>
        {children}
      </div>
    )
  }

  // Render with quota status indicator
  return (
    <div className={`relative ${className}`}>
      {/* Main content */}
      <div
        className={
          canPerform ? '' : 'opacity-50 pointer-events-none select-none'
        }
        onClick={handleActionAttempt}
      >
        {children}
      </div>

      {/* Quota status overlay */}
      <div className={`mt-3 p-3 border rounded-lg ${styling.containerClass}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <StatusIcon className={`h-4 w-4 ${styling.iconClass}`} />
            <div className="text-sm">
              <div className={`font-medium ${styling.textClass}`}>
                {!canPerform
                  ? `${limitType.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())} Limit Reached`
                  : usage >= 90
                    ? `Near ${limitType.replace('_', ' ')} Limit`
                    : `${limitStatus.remaining} Remaining`}
              </div>
              <div className={`text-xs ${styling.textClass} opacity-75`}>
                {limitStatus.message}
                {!canPerform && ' - Action blocked'}
              </div>
            </div>
          </div>

          {/* Usage indicator */}
          <div className="flex items-center space-x-3">
            <div className="text-xs font-mono">
              {limitStatus.current}/{limitStatus.max}
            </div>

            {canUpgrade() && (usage >= showWarningThreshold || !canPerform) && (
              <button
                onClick={handleUpgradeClick}
                className={`inline-flex items-center px-2.5 py-1 border border-transparent text-xs font-medium rounded transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                  !canPerform
                    ? 'text-red-700 bg-red-100 hover:bg-red-200 dark:text-red-200 dark:bg-red-900 dark:hover:bg-red-800 focus:ring-red-500'
                    : usage >= 90
                      ? 'text-amber-700 bg-amber-100 hover:bg-amber-200 dark:text-amber-200 dark:bg-amber-900 dark:hover:bg-amber-800 focus:ring-amber-500'
                      : 'text-blue-700 bg-blue-100 hover:bg-blue-200 dark:text-blue-200 dark:bg-blue-900 dark:hover:bg-blue-800 focus:ring-blue-500'
                }`}
              >
                <ArrowUpIcon className="h-3 w-3 mr-1" />
                {!canPerform ? 'Upgrade' : 'More Quota'}
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-2">
          <div className="flex justify-between text-xs mb-1">
            <span className={styling.textClass}>Usage</span>
            <span className={`font-medium ${styling.textClass}`}>
              {Math.round(usage)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all duration-300 ${
                !canPerform
                  ? 'bg-red-500'
                  : usage >= 90
                    ? 'bg-amber-500'
                    : usage >= showWarningThreshold
                      ? 'bg-blue-500'
                      : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(usage, 100)}%` }}
            />
          </div>
        </div>

        {/* Upgrade message */}
        {(usage >= showWarningThreshold || !canPerform) && (
          <div className={`mt-2 text-xs ${styling.textClass} opacity-75`}>
            {customUpgradeMessage || getUpgradeMessage(limitType)}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Convenient wrapper components for common actions
 */
export const PostCreationGuard = ({ children, ...props }) => (
  <ActionQuotaGuard
    action="create"
    limitType="posts"
    customUpgradeMessage="Upgrade for more daily posts and advanced scheduling"
    {...props}
  >
    {children}
  </ActionQuotaGuard>
)

export const ImageGenerationGuard = ({ children, ...props }) => (
  <ActionQuotaGuard
    action="generate"
    limitType="images"
    customUpgradeMessage="Upgrade for more AI-generated images and premium models"
    {...props}
  >
    {children}
  </ActionQuotaGuard>
)

export const SocialProfileGuard = ({ children, ...props }) => (
  <ActionQuotaGuard
    action="add"
    limitType="social_profiles"
    customUpgradeMessage="Upgrade to connect unlimited social media accounts"
    {...props}
  >
    {children}
  </ActionQuotaGuard>
)

export const TeamMemberGuard = ({ children, ...props }) => (
  <ActionQuotaGuard
    action="add"
    limitType="team"
    customUpgradeMessage="Upgrade to invite more team members and collaborate"
    {...props}
  >
    {children}
  </ActionQuotaGuard>
)

export default ActionQuotaGuard
