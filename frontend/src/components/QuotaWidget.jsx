import React from 'react'
import { usePlan } from '../contexts/PlanContext'
import { Link } from 'react-router-dom'
import {
  DocumentTextIcon,
  PhotoIcon,
  UserIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowUpIcon,
} from '@heroicons/react/24/outline'

const QuotaWidget = ({ compact = false, showAllLimits = true }) => {
  const { limits, plan, canUpgrade, getUpgradeMessage } = usePlan()

  if (!limits || !plan) return null

  const quotaItems = [
    {
      type: 'posts',
      label: 'Posts Today',
      icon: DocumentTextIcon,
      current: limits.posts?.current || 0,
      max: limits.posts?.daily_limit || 0,
      color: 'blue',
    },
    {
      type: 'images',
      label: 'Images This Month',
      icon: PhotoIcon,
      current: limits.images?.current || 0,
      max: limits.images?.monthly_limit || 0,
      color: 'green',
    },
    {
      type: 'social_profiles',
      label: 'Social Profiles',
      icon: UserIcon,
      current: limits.social_profiles?.current || 0,
      max: limits.social_profiles?.max || 1,
      color: 'purple',
    },
  ].filter((item, index) => showAllLimits || index < 2) // Show first 2 if compact

  const getUsageStatus = (current, max) => {
    const percentage = (current / max) * 100
    if (percentage >= 90) return { status: 'critical', color: 'red' }
    if (percentage >= 75) return { status: 'warning', color: 'yellow' }
    return { status: 'good', color: 'green' }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'critical':
        return ExclamationTriangleIcon
      case 'warning':
        return ExclamationTriangleIcon
      default:
        return CheckCircleIcon
    }
  }

  if (compact) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Usage Status
          </h3>
          <Link
            to="/billing"
            className="text-xs text-blue-600 hover:text-blue-500 font-medium"
          >
            View All →
          </Link>
        </div>

        <div className="space-y-3">
          {quotaItems.slice(0, 2).map((item) => {
            const { status, color } = getUsageStatus(item.current, item.max)
            const StatusIcon = getStatusIcon(status)
            const percentage = (item.current / item.max) * 100

            return (
              <div
                key={item.type}
                className="flex items-center justify-between"
              >
                <div className="flex items-center space-x-2">
                  <div
                    className={`p-1 rounded bg-${item.color}-100 dark:bg-${item.color}-900`}
                  >
                    <item.icon
                      className={`h-3 w-3 text-${item.color}-600 dark:text-${item.color}-400`}
                    />
                  </div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {item.label}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-medium text-gray-900 dark:text-white">
                    {item.current}/{item.max}
                  </span>
                  <StatusIcon className={`h-3 w-3 text-${color}-500`} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Usage & Quotas
          </h3>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">
              Plan: {plan.display_name}
            </span>
            {canUpgrade() && (
              <Link
                to="/billing"
                className="inline-flex items-center text-sm text-blue-600 hover:text-blue-500 font-medium"
              >
                <ArrowUpIcon className="h-4 w-4 mr-1" />
                Upgrade
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quotaItems.map((item) => {
            const { status, color } = getUsageStatus(item.current, item.max)
            const StatusIcon = getStatusIcon(status)
            const percentage = Math.min((item.current / item.max) * 100, 100)

            return (
              <div key={item.type} className="text-center">
                <div
                  className={`inline-flex p-3 rounded-lg bg-${item.color}-100 dark:bg-${item.color}-900 mb-3`}
                >
                  <item.icon
                    className={`h-6 w-6 text-${item.color}-600 dark:text-${item.color}-400`}
                  />
                </div>

                <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                  {item.current} / {item.max}
                </div>

                <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  {item.label}
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 bg-${color}-500`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>

                {/* Status indicator */}
                <div className="flex items-center justify-center space-x-1">
                  <StatusIcon className={`h-4 w-4 text-${color}-500`} />
                  <span className={`text-xs font-medium text-${color}-600`}>
                    {status === 'critical'
                      ? 'Limit Reached'
                      : status === 'warning'
                        ? 'Near Limit'
                        : `${Math.round(percentage)}% Used`}
                  </span>
                </div>

                {/* Upgrade prompt for critical/warning status */}
                {status !== 'good' && canUpgrade() && (
                  <div className="mt-3">
                    <Link
                      to="/billing"
                      className={`inline-block px-3 py-1 text-xs font-medium rounded ${
                        status === 'critical'
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                      } transition-colors`}
                    >
                      Upgrade Plan
                    </Link>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Overall status message */}
        <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {plan.display_name} Plan
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {quotaItems.some(
                  (item) =>
                    getUsageStatus(item.current, item.max).status !== 'good'
                )
                  ? 'Some limits are being reached. Consider upgrading for more capacity.'
                  : 'All systems running smoothly within your plan limits.'}
              </p>
            </div>
            {canUpgrade() && (
              <Link
                to="/billing"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                <ArrowUpIcon className="h-4 w-4 mr-2" />
                Upgrade
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default QuotaWidget
