import React, { useState, useEffect } from 'react'
import {
  BellIcon,
  BellSlashIcon,
  CogIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ClockIcon,
  DevicePhoneMobileIcon,
  ComputerDesktopIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '../../contexts/AuthContext'
import { useNotifications } from '../../hooks/useNotifications'

// Notification preference categories
const NOTIFICATION_CATEGORIES = {
  system: {
    label: 'System Notifications',
    description: 'Critical system alerts and status updates',
    icon: CogIcon,
    types: {
      errors: { label: 'System Errors', default: true, priority: 'high' },
      maintenance: {
        label: 'Maintenance Alerts',
        default: true,
        priority: 'medium',
      },
      updates: { label: 'System Updates', default: false, priority: 'low' },
    },
  },
  content: {
    label: 'Content Operations',
    description: 'Publishing, scheduling, and content management',
    icon: CheckCircleIcon,
    types: {
      published: {
        label: 'Content Published',
        default: true,
        priority: 'medium',
      },
      scheduled: {
        label: 'Content Scheduled',
        default: false,
        priority: 'low',
      },
      failed: { label: 'Publishing Failures', default: true, priority: 'high' },
      approved: { label: 'Content Approved', default: false, priority: 'low' },
    },
  },
  workflow: {
    label: 'Workflow & Automation',
    description: 'Automated workflows and background processes',
    icon: ArrowPathIcon,
    types: {
      completed: {
        label: 'Workflow Completed',
        default: true,
        priority: 'medium',
      },
      failed: { label: 'Workflow Failed', default: true, priority: 'high' },
      paused: { label: 'Workflow Paused', default: false, priority: 'medium' },
      scheduled: {
        label: 'Workflow Scheduled',
        default: false,
        priority: 'low',
      },
    },
  },
  account: {
    label: 'Account & Billing',
    description: 'Account status, billing, and subscription updates',
    icon: InformationCircleIcon,
    types: {
      billing: { label: 'Billing Issues', default: true, priority: 'high' },
      limits: { label: 'Usage Limits', default: true, priority: 'medium' },
      expiry: { label: 'Subscription Expiry', default: true, priority: 'high' },
      upgrade: { label: 'Upgrade Reminders', default: false, priority: 'low' },
    },
  },
}

const RETRY_STRATEGIES = {
  immediate: {
    label: 'Immediate',
    description: 'Retry failed operations immediately',
    delays: [1000, 2000, 5000],
  },
  gradual: {
    label: 'Gradual',
    description: 'Retry with increasing delays',
    delays: [2000, 5000, 15000],
  },
  patient: {
    label: 'Patient',
    description: 'Retry with long delays to avoid server load',
    delays: [5000, 15000, 60000],
  },
  manual: {
    label: 'Manual Only',
    description: 'Only retry when manually triggered',
    delays: [],
  },
}

const DELIVERY_METHODS = {
  toast: {
    label: 'Toast Notifications',
    description: 'Show notifications as toast popups',
    icon: DevicePhoneMobileIcon,
    supported: true,
  },
  inbox: {
    label: 'In-App Inbox',
    description: 'Store notifications in the app inbox',
    icon: BellIcon,
    supported: true,
  },
  desktop: {
    label: 'Desktop Notifications',
    description: 'Send native desktop notifications',
    icon: ComputerDesktopIcon,
    supported: 'Notification' in window,
  },
  email: {
    label: 'Email Notifications',
    description: 'Send notifications via email',
    icon: InformationCircleIcon,
    supported: false, // Would need backend implementation
  },
}

export default function NotificationPreferences({ onClose }) {
  const [preferences, setPreferences] = useState({
    enabled: true,
    categories: {},
    retryStrategy: 'gradual',
    deliveryMethods: {
      toast: true,
      inbox: true,
      desktop: false,
      email: false,
    },
    doNotDisturb: {
      enabled: false,
      startTime: '22:00',
      endTime: '08:00',
    },
    priority: {
      high: true,
      medium: true,
      low: false,
    },
    persistence: {
      errors: true,
      success: false,
      warnings: true,
      info: false,
    },
    maxConcurrent: 3,
    autoClose: true,
    soundEnabled: false,
  })

  const [isLoading, setIsLoading] = useState(true)
  const [hasChanges, setHasChanges] = useState(false)
  const [permissionStatus, setPermissionStatus] = useState({
    notifications: 'default',
  })

  const { isAuthenticated } = useAuth()
  const { showSuccess, showError } = useNotifications()

  // Load preferences from localStorage/API on mount
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const stored = localStorage.getItem('notificationPreferences')
        if (stored) {
          const parsed = JSON.parse(stored)

          // Initialize categories with defaults if not present
          const categories = {}
          Object.entries(NOTIFICATION_CATEGORIES).forEach(
            ([categoryKey, category]) => {
              categories[categoryKey] = {}
              Object.entries(category.types).forEach(([typeKey, type]) => {
                categories[categoryKey][typeKey] =
                  parsed.categories?.[categoryKey]?.[typeKey] ?? type.default
              })
            }
          )

          setPreferences({
            ...preferences,
            ...parsed,
            categories,
          })
        } else {
          // Initialize with defaults
          const categories = {}
          Object.entries(NOTIFICATION_CATEGORIES).forEach(
            ([categoryKey, category]) => {
              categories[categoryKey] = {}
              Object.entries(category.types).forEach(([typeKey, type]) => {
                categories[categoryKey][typeKey] = type.default
              })
            }
          )

          setPreferences((prev) => ({ ...prev, categories }))
        }

        // Check notification permissions
        if ('Notification' in window) {
          setPermissionStatus({
            notifications: Notification.permission,
          })
        }
      } catch (error) {
        console.error('Failed to load notification preferences:', error)
      } finally {
        setIsLoading(false)
      }
    }

    loadPreferences()
  }, [])

  // Save preferences
  const savePreferences = async () => {
    try {
      localStorage.setItem(
        'notificationPreferences',
        JSON.stringify(preferences)
      )

      // TODO: Save to backend API when available
      // await api.user.updateNotificationPreferences(preferences)

      showSuccess('Notification preferences saved', 'Settings Updated')
      setHasChanges(false)

      // Dispatch event for other components to update
      window.dispatchEvent(
        new CustomEvent('notificationPreferencesChanged', {
          detail: preferences,
        })
      )
    } catch (error) {
      console.error('Failed to save preferences:', error)
      showError('Failed to save notification preferences', 'Save Error')
    }
  }

  // Request notification permissions
  const requestPermissions = async () => {
    if ('Notification' in window) {
      try {
        const permission = await Notification.requestPermission()
        setPermissionStatus({ notifications: permission })

        if (permission === 'granted') {
          showSuccess('Desktop notifications enabled', 'Permission Granted')
          setPreferences((prev) => ({
            ...prev,
            deliveryMethods: { ...prev.deliveryMethods, desktop: true },
          }))
          setHasChanges(true)
        } else {
          showError('Desktop notifications blocked', 'Permission Denied')
        }
      } catch (error) {
        console.error('Failed to request notification permission:', error)
        showError(
          'Failed to request notification permissions',
          'Permission Error'
        )
      }
    }
  }

  // Update category preferences
  const updateCategoryType = (category, type, enabled) => {
    setPreferences((prev) => ({
      ...prev,
      categories: {
        ...prev.categories,
        [category]: {
          ...prev.categories[category],
          [type]: enabled,
        },
      },
    }))
    setHasChanges(true)
  }

  // Update general preferences
  const updatePreference = (key, value) => {
    setPreferences((prev) => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  // Update nested preferences
  const updateNestedPreference = (parentKey, childKey, value) => {
    setPreferences((prev) => ({
      ...prev,
      [parentKey]: { ...prev[parentKey], [childKey]: value },
    }))
    setHasChanges(true)
  }

  // Test notification
  const testNotification = () => {
    const event = new CustomEvent('createEnhancedNotification', {
      detail: {
        type: 'info',
        title: 'Test Notification',
        message: 'This is a test notification with your current preferences',
        duration: 5000,
        actions: [
          {
            label: 'Got it',
            onClick: () => {},
            style: 'text-blue-600 hover:text-blue-500',
          },
        ],
      },
    })
    window.dispatchEvent(event)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <ArrowPathIcon className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Notification Preferences
        </h2>
        <p className="text-gray-600">
          Customize how and when you receive notifications from the platform
        </p>
      </div>

      {/* Master toggle */}
      <div className="mb-8 p-6 bg-white rounded-lg border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {preferences.enabled ? (
              <BellIcon className="h-6 w-6 text-blue-500" />
            ) : (
              <BellSlashIcon className="h-6 w-6 text-gray-400" />
            )}
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                All Notifications
              </h3>
              <p className="text-sm text-gray-600">
                {preferences.enabled
                  ? 'Notifications are enabled'
                  : 'All notifications are disabled'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={testNotification}
              className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Test
            </button>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.enabled}
                onChange={(e) => updatePreference('enabled', e.target.checked)}
                className="sr-only"
              />
              <div
                className={`w-11 h-6 rounded-full transition-colors ${
                  preferences.enabled ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <div
                  className={`dot absolute w-4 h-4 rounded-full transition-transform bg-white top-1 ${
                    preferences.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </div>
            </label>
          </div>
        </div>
      </div>

      {preferences.enabled && (
        <>
          {/* Delivery Methods */}
          <div className="mb-8 p-6 bg-white rounded-lg border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Delivery Methods
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(DELIVERY_METHODS).map(([key, method]) => (
                <div
                  key={key}
                  className={`p-4 border rounded-lg transition-colors ${
                    method.supported
                      ? 'border-gray-200 hover:bg-gray-50'
                      : 'border-gray-100 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <method.icon
                        className={`h-5 w-5 ${
                          method.supported ? 'text-gray-600' : 'text-gray-400'
                        }`}
                      />
                      <div>
                        <p
                          className={`font-medium ${
                            method.supported ? 'text-gray-900' : 'text-gray-500'
                          }`}
                        >
                          {method.label}
                        </p>
                        <p className="text-sm text-gray-500">
                          {method.description}
                        </p>
                      </div>
                    </div>
                    {method.supported && (
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={preferences.deliveryMethods[key]}
                          onChange={(e) =>
                            updateNestedPreference(
                              'deliveryMethods',
                              key,
                              e.target.checked
                            )
                          }
                          className="sr-only"
                        />
                        <div
                          className={`w-8 h-4 rounded-full transition-colors ${
                            preferences.deliveryMethods[key]
                              ? 'bg-blue-600'
                              : 'bg-gray-200'
                          }`}
                        >
                          <div
                            className={`dot absolute w-3 h-3 rounded-full transition-transform bg-white top-0.5 ${
                              preferences.deliveryMethods[key]
                                ? 'translate-x-4'
                                : 'translate-x-0.5'
                            }`}
                          />
                        </div>
                      </label>
                    )}
                  </div>

                  {key === 'desktop' &&
                    method.supported &&
                    permissionStatus.notifications !== 'granted' && (
                      <button
                        onClick={requestPermissions}
                        className="mt-2 text-sm text-blue-600 hover:text-blue-500"
                      >
                        Enable desktop notifications
                      </button>
                    )}
                </div>
              ))}
            </div>
          </div>

          {/* Retry Strategy */}
          <div className="mb-8 p-6 bg-white rounded-lg border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Retry Strategy
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Choose how failed operations should be retried
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(RETRY_STRATEGIES).map(([key, strategy]) => (
                <label key={key} className="cursor-pointer">
                  <div
                    className={`p-4 border rounded-lg transition-colors ${
                      preferences.retryStrategy === key
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center mb-2">
                      <input
                        type="radio"
                        name="retryStrategy"
                        value={key}
                        checked={preferences.retryStrategy === key}
                        onChange={(e) =>
                          updatePreference('retryStrategy', e.target.value)
                        }
                        className="h-4 w-4 text-blue-600"
                      />
                      <span className="ml-2 font-medium text-gray-900">
                        {strategy.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      {strategy.description}
                    </p>
                    {strategy.delays.length > 0 && (
                      <p className="text-xs text-gray-400 mt-1">
                        Delays:{' '}
                        {strategy.delays.map((d) => `${d / 1000}s`).join(', ')}
                      </p>
                    )}
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Notification Categories */}
          <div className="mb-8 p-6 bg-white rounded-lg border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Notification Categories
            </h3>
            <div className="space-y-6">
              {Object.entries(NOTIFICATION_CATEGORIES).map(
                ([categoryKey, category]) => (
                  <div
                    key={categoryKey}
                    className="border border-gray-100 rounded-lg p-4"
                  >
                    <div className="flex items-center space-x-3 mb-4">
                      <category.icon className="h-5 w-5 text-gray-600" />
                      <div>
                        <h4 className="font-medium text-gray-900">
                          {category.label}
                        </h4>
                        <p className="text-sm text-gray-500">
                          {category.description}
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(category.types).map(([typeKey, type]) => (
                        <label
                          key={typeKey}
                          className="flex items-center justify-between"
                        >
                          <div>
                            <span className="text-sm font-medium text-gray-700">
                              {type.label}
                            </span>
                            <span
                              className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                                type.priority === 'high'
                                  ? 'bg-red-100 text-red-800'
                                  : type.priority === 'medium'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {type.priority}
                            </span>
                          </div>
                          <input
                            type="checkbox"
                            checked={
                              preferences.categories[categoryKey]?.[typeKey] ||
                              false
                            }
                            onChange={(e) =>
                              updateCategoryType(
                                categoryKey,
                                typeKey,
                                e.target.checked
                              )
                            }
                            className="h-4 w-4 text-blue-600 rounded"
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="p-6 bg-white rounded-lg border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Advanced Settings
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Maximum Concurrent Notifications
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={preferences.maxConcurrent}
                  onChange={(e) =>
                    updatePreference('maxConcurrent', parseInt(e.target.value))
                  }
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1</span>
                  <span>{preferences.maxConcurrent}</span>
                  <span>10</span>
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    Auto-close notifications
                  </span>
                  <input
                    type="checkbox"
                    checked={preferences.autoClose}
                    onChange={(e) =>
                      updatePreference('autoClose', e.target.checked)
                    }
                    className="h-4 w-4 text-blue-600 rounded"
                  />
                </label>

                <label className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    Notification sounds
                  </span>
                  <input
                    type="checkbox"
                    checked={preferences.soundEnabled}
                    onChange={(e) =>
                      updatePreference('soundEnabled', e.target.checked)
                    }
                    className="h-4 w-4 text-blue-600 rounded"
                  />
                </label>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200">
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          Cancel
        </button>
        <div className="flex space-x-3">
          <button
            onClick={() => {
              // Reset to defaults
              const categories = {}
              Object.entries(NOTIFICATION_CATEGORIES).forEach(
                ([categoryKey, category]) => {
                  categories[categoryKey] = {}
                  Object.entries(category.types).forEach(([typeKey, type]) => {
                    categories[categoryKey][typeKey] = type.default
                  })
                }
              )

              setPreferences({
                enabled: true,
                categories,
                retryStrategy: 'gradual',
                deliveryMethods: {
                  toast: true,
                  inbox: true,
                  desktop: false,
                  email: false,
                },
                doNotDisturb: {
                  enabled: false,
                  startTime: '22:00',
                  endTime: '08:00',
                },
                priority: { high: true, medium: true, low: false },
                persistence: {
                  errors: true,
                  success: false,
                  warnings: true,
                  info: false,
                },
                maxConcurrent: 3,
                autoClose: true,
                soundEnabled: false,
              })
              setHasChanges(true)
            }}
            className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Reset to Defaults
          </button>
          <button
            onClick={savePreferences}
            disabled={!hasChanges}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  )
}
