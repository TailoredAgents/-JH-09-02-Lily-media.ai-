import React, { useEffect, useState } from 'react'
import { usePlan } from '../contexts/PlanContext'
import { useNotifications } from '../hooks/useNotifications'
import { Link } from 'react-router-dom'
import {
  ExclamationTriangleIcon,
  XMarkIcon,
  ArrowUpIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

const UsageNotifications = () => {
  const { limits, plan, canUpgrade, getUpgradeMessage } = usePlan()
  const { showInfo, showWarning } = useNotifications()
  const [dismissedNotifications, setDismissedNotifications] = useState(
    new Set()
  )

  useEffect(() => {
    if (!limits || !plan) return

    // Check all limits and show notifications for critical/warning status
    const checkLimits = [
      {
        type: 'posts',
        current: limits.posts?.current || 0,
        max: limits.posts?.daily_limit || 0,
        label: 'daily posts',
      },
      {
        type: 'images',
        current: limits.images?.current || 0,
        max: limits.images?.monthly_limit || 0,
        label: 'monthly images',
      },
      {
        type: 'social_profiles',
        current: limits.social_profiles?.current || 0,
        max: limits.social_profiles?.max || 1,
        label: 'social profiles',
      },
    ]

    checkLimits.forEach((limit) => {
      const percentage = (limit.current / limit.max) * 100
      const notificationId = `${limit.type}-${percentage >= 90 ? 'critical' : 'warning'}`

      // Skip if already dismissed
      if (dismissedNotifications.has(notificationId)) return

      if (percentage >= 90) {
        // Critical - at or near limit
        showWarning(
          `You've reached your ${limit.label} limit (${limit.current}/${limit.max}). ${canUpgrade() ? 'Upgrade your plan for more capacity.' : 'Consider upgrading for more capacity.'}`,
          'Usage Limit Reached',
          8000 // Show longer for critical
        )
      } else if (percentage >= 80) {
        // Warning - approaching limit
        showInfo(
          `You're approaching your ${limit.label} limit (${limit.current}/${limit.max}). ${canUpgrade() ? 'Consider upgrading to avoid interruptions.' : ''}`,
          'Approaching Usage Limit',
          5000
        )
      }
    })
  }, [limits, plan, canUpgrade, showInfo, showWarning, dismissedNotifications])

  const dismissNotification = (notificationId) => {
    setDismissedNotifications((prev) => new Set([...prev, notificationId]))
  }

  if (!limits || !plan) return null

  // Create persistent banners for critical issues
  const criticalLimits = [
    {
      type: 'posts',
      current: limits.posts?.current || 0,
      max: limits.posts?.daily_limit || 0,
      label: 'Posts Today',
    },
    {
      type: 'images',
      current: limits.images?.current || 0,
      max: limits.images?.monthly_limit || 0,
      label: 'Images This Month',
    },
    {
      type: 'social_profiles',
      current: limits.social_profiles?.current || 0,
      max: limits.social_profiles?.max || 1,
      label: 'Social Profiles',
    },
  ].filter((limit) => {
    const percentage = (limit.current / limit.max) * 100
    return (
      percentage >= 95 && !dismissedNotifications.has(`banner-${limit.type}`)
    )
  })

  if (criticalLimits.length === 0) return null

  return (
    <div className="space-y-2">
      {criticalLimits.map((limit) => {
        const notificationId = `banner-${limit.type}`

        return (
          <div
            key={limit.type}
            className="bg-red-50 border border-red-200 rounded-lg p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                <div>
                  <h4 className="text-sm font-semibold text-red-800">
                    {limit.label} Limit Reached
                  </h4>
                  <p className="text-sm text-red-700">
                    You've used {limit.current} of {limit.max}{' '}
                    {limit.label.toLowerCase()}.
                    {canUpgrade() && ' Upgrade your plan for unlimited access.'}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {canUpgrade() && (
                  <Link
                    to="/billing"
                    className="inline-flex items-center px-3 py-1.5 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition-colors"
                  >
                    <ArrowUpIcon className="h-4 w-4 mr-1" />
                    Upgrade
                  </Link>
                )}
                <button
                  onClick={() => dismissNotification(notificationId)}
                  className="text-red-500 hover:text-red-700 transition-colors"
                  aria-label="Dismiss notification"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default UsageNotifications
