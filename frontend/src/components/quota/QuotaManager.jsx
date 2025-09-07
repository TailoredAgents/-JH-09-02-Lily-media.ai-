import React, { useState, useEffect } from 'react'
import { usePlan } from '../../contexts/PlanContext'
import { usePlanConditionals } from '../../hooks/usePlanConditionals'
import { useNotifications } from '../../hooks/useNotifications'
import { EnhancedUsageIndicator } from '../enhanced/EnhancedPlanGate'
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  UserGroupIcon,
  DocumentTextIcon,
  PhotoIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'

/**
 * Centralized Quota Management Component
 *
 * Provides comprehensive usage monitoring and upgrade flows
 * with proactive notifications and smart recommendations
 */
const QuotaManager = ({
  showHeader = true,
  compactMode = false,
  limitTypes = ['posts', 'images', 'social_profiles', 'team', 'workspaces'],
  showUpgradePrompts = true,
  autoRefresh = true,
}) => {
  const { plan, limits, refreshLimits } = usePlan()
  const {
    postsAtLimit,
    imagesAtLimit,
    profilesAtLimit,
    postsNearLimit,
    imagesNearLimit,
    profilesNearLimit,
    canUpgrade,
    getUpgradeMessage,
  } = usePlanConditionals()
  const { showWarning, showError } = useNotifications()

  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [criticalAlerts, setCriticalAlerts] = useState([])

  // Auto-refresh limits every 5 minutes
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(
      async () => {
        try {
          await refreshLimits()
          setLastRefresh(new Date())
        } catch (error) {
          console.error('Failed to refresh limits:', error)
        }
      },
      5 * 60 * 1000
    ) // 5 minutes

    return () => clearInterval(interval)
  }, [autoRefresh, refreshLimits])

  // Monitor for critical usage alerts
  useEffect(() => {
    const alerts = []

    if (postsAtLimit()) {
      alerts.push({
        type: 'posts',
        severity: 'critical',
        title: 'Daily post limit reached',
        message: 'You cannot create more posts today',
        icon: DocumentTextIcon,
      })
    } else if (postsNearLimit()) {
      alerts.push({
        type: 'posts',
        severity: 'warning',
        title: 'Near daily post limit',
        message: "You're close to your daily posting limit",
        icon: DocumentTextIcon,
      })
    }

    if (imagesAtLimit()) {
      alerts.push({
        type: 'images',
        severity: 'critical',
        title: 'Image generation limit reached',
        message: 'You cannot generate more images this month',
        icon: PhotoIcon,
      })
    } else if (imagesNearLimit()) {
      alerts.push({
        type: 'images',
        severity: 'warning',
        title: 'Near image generation limit',
        message: "You're close to your monthly image limit",
        icon: PhotoIcon,
      })
    }

    if (profilesAtLimit()) {
      alerts.push({
        type: 'profiles',
        severity: 'critical',
        title: 'Social profile limit reached',
        message: 'You cannot connect more social accounts',
        icon: UserGroupIcon,
      })
    }

    setCriticalAlerts(alerts)

    // Show notifications for critical alerts
    alerts.forEach((alert) => {
      if (alert.severity === 'critical') {
        showError(`${alert.title}: ${alert.message}`)
      } else if (alert.severity === 'warning') {
        showWarning(`${alert.title}: ${alert.message}`)
      }
    })
  }, [
    limits,
    postsAtLimit,
    imagesAtLimit,
    profilesAtLimit,
    postsNearLimit,
    imagesNearLimit,
    profilesNearLimit,
    showWarning,
    showError,
  ])

  const getLimitIcon = (limitType) => {
    switch (limitType) {
      case 'posts':
        return DocumentTextIcon
      case 'images':
        return PhotoIcon
      case 'social_profiles':
        return UserGroupIcon
      case 'team':
        return UserGroupIcon
      case 'workspaces':
        return CpuChipIcon
      default:
        return ChartBarIcon
    }
  }

  const getLimitDisplayName = (limitType) => {
    switch (limitType) {
      case 'posts':
        return 'Daily Posts'
      case 'images':
        return 'Monthly Images'
      case 'social_profiles':
        return 'Social Profiles'
      case 'team':
        return 'Team Members'
      case 'workspaces':
        return 'Workspaces'
      default:
        return limitType
          .replace('_', ' ')
          .replace(/\b\w/g, (l) => l.toUpperCase())
    }
  }

  const handleUpgradeClick = () => {
    window.location.href = '/billing'
  }

  if (!limits) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-${compactMode ? '4' : '6'}`}>
      {/* Header */}
      {showHeader && (
        <div className="flex items-center justify-between">
          <div>
            <h2
              className={`${compactMode ? 'text-lg' : 'text-xl'} font-semibold text-gray-900 dark:text-white flex items-center`}
            >
              <ChartBarIcon className="h-5 w-5 mr-2" />
              Usage & Quotas
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Monitor your usage across all plan limits
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
              <ClockIcon className="h-3 w-3 mr-1" />
              Updated {lastRefresh.toLocaleTimeString()}
            </div>

            {canUpgrade() && showUpgradePrompts && (
              <button
                onClick={handleUpgradeClick}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
                Upgrade Plan
              </button>
            )}
          </div>
        </div>
      )}

      {/* Critical Alerts */}
      {criticalAlerts.length > 0 && (
        <div className="space-y-3">
          {criticalAlerts.map((alert, index) => {
            const Icon = alert.icon
            return (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  alert.severity === 'critical'
                    ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    : 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Icon
                      className={`h-5 w-5 mr-3 ${
                        alert.severity === 'critical'
                          ? 'text-red-500'
                          : 'text-amber-500'
                      }`}
                    />
                    <div>
                      <h3
                        className={`text-sm font-medium ${
                          alert.severity === 'critical'
                            ? 'text-red-900 dark:text-red-100'
                            : 'text-amber-900 dark:text-amber-100'
                        }`}
                      >
                        {alert.title}
                      </h3>
                      <p
                        className={`text-sm ${
                          alert.severity === 'critical'
                            ? 'text-red-700 dark:text-red-300'
                            : 'text-amber-700 dark:text-amber-300'
                        }`}
                      >
                        {alert.message}
                      </p>
                    </div>
                  </div>

                  {canUpgrade() && showUpgradePrompts && (
                    <button
                      onClick={handleUpgradeClick}
                      className={`ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded ${
                        alert.severity === 'critical'
                          ? 'text-red-700 bg-red-100 hover:bg-red-200 dark:text-red-200 dark:bg-red-900 dark:hover:bg-red-800'
                          : 'text-amber-700 bg-amber-100 hover:bg-amber-200 dark:text-amber-200 dark:bg-amber-900 dark:hover:bg-amber-800'
                      } transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500`}
                    >
                      <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                      Upgrade Now
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Usage Indicators */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className={`grid grid-cols-1 ${compactMode ? 'gap-4' : 'gap-6'}`}>
          {limitTypes.map((limitType) => {
            if (!limits[limitType]) return null

            const Icon = getLimitIcon(limitType)
            const displayName = getLimitDisplayName(limitType)

            return (
              <div key={limitType}>
                {!compactMode && (
                  <div className="flex items-center mb-3">
                    <Icon className="h-5 w-5 text-gray-500 mr-2" />
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      {displayName}
                    </h3>
                  </div>
                )}

                <EnhancedUsageIndicator
                  limitType={limitType}
                  showUpgradePrompt={showUpgradePrompts}
                  showPercentage={!compactMode}
                  showRemaining={!compactMode}
                  size={compactMode ? 'small' : 'default'}
                />
              </div>
            )
          })}
        </div>
      </div>

      {/* Plan Summary */}
      {plan && !compactMode && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Current Plan: {plan.display_name || plan.plan_name}
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {canUpgrade()
                  ? 'Upgrade anytime for higher limits and premium features'
                  : "You're on our highest tier plan"}
              </p>
            </div>

            {canUpgrade() && (
              <button
                onClick={handleUpgradeClick}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                <ArrowTrendingUpIcon className="h-4 w-4 mr-2" />
                View Plans
              </button>
            )}
          </div>
        </div>
      )}

      {/* Usage Tips */}
      {!compactMode && criticalAlerts.length === 0 && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-start">
            <ChartBarIcon className="h-5 w-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-medium text-green-900 dark:text-green-100 mb-1">
                Usage Looking Good!
              </h3>
              <div className="text-sm text-green-700 dark:text-green-300 space-y-1">
                <p>• Your usage is within healthy limits</p>
                <p>• Limits reset daily (posts) and monthly (images)</p>
                <p>• Monitor this dashboard to avoid interruptions</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default QuotaManager
