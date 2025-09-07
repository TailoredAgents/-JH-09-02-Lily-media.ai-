import React, { useState, useMemo, useCallback, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import { usePlan } from '../contexts/PlanContext'
import { useEnhancedApi } from '../hooks/useEnhancedApi'
import { useNotifications } from '../hooks/useNotifications'
import NotificationSystem from './Notifications/NotificationSystem'
import ThemeToggle from './ThemeToggle'
import PlanGate, { UsageLimitIndicator } from './PlanGate'
import UsageNotifications from './UsageNotifications'
import {
  getIconAltText,
  getNavLinkProps,
  getButtonProps,
  getImageAltText,
} from '../utils/accessibility'
import {
  HomeIcon,
  CalendarDaysIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  Bars3Icon,
  XMarkIcon,
  CpuChipIcon,
  ArrowRightOnRectangleIcon,
  PlusIcon,
  ExclamationTriangleIcon,
  InboxIcon,
  LinkIcon,
  CreditCardIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'

// Base navigation items
const baseNavigation = [
  { name: 'Flight Deck', href: '/dashboard', icon: HomeIcon },
  { name: 'Social Inbox', href: '/inbox', icon: InboxIcon },
  { name: 'Create Post', href: '/create-post', icon: PlusIcon },
  { name: 'Content Library', href: '/content', icon: DocumentTextIcon },
  { name: 'Scheduler', href: '/calendar', icon: CalendarDaysIcon },
  { name: 'Brand Brain', href: '/memory', icon: CpuChipIcon },
]

// Conditionally add Integrations if feature flag is enabled
const integrationsItem =
  import.meta.env.VITE_FEATURE_PARTNER_OAUTH === 'true'
    ? { name: 'Integrations', href: '/integrations', icon: LinkIcon }
    : null

// Billing should come before settings
const billingItem = { name: 'Billing', href: '/billing', icon: CreditCardIcon }

// Settings should always be last
const settingsItem = {
  name: 'Settings',
  href: '/settings',
  icon: Cog6ToothIcon,
}

// Construct final navigation array
const navigation = [
  ...baseNavigation,
  ...(integrationsItem ? [integrationsItem] : []),
  billingItem,
  settingsItem,
]

function classNames(...classes) {
  return classes.filter(Boolean).join(' ')
}

function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const location = useLocation()
  const { user, logout, isAuthenticated } = useAuth()
  const { plan, limits, hasEnhancedAutopilot } = usePlan()
  const { api } = useEnhancedApi()
  const { showSuccess, showError } = useNotifications()

  // Autonomous mode state
  const [autopilotMode, setAutopilotMode] = useState(false)
  const [loadingAutopilot, setLoadingAutopilot] = useState(false)
  const [settingsLoaded, setSettingsLoaded] = useState(false)

  // Memoize navigation items to prevent re-creation on every render
  const navigationItems = useMemo(() => {
    return navigation.filter((item) => {
      // No gating for core pages
      if (
        [
          'Flight Deck',
          'Create Post',
          'Content Library',
          'Scheduler',
          'Settings',
          'Billing',
        ].includes(item.name)
      ) {
        return true
      }

      // Gate specific features based on plan
      switch (item.name) {
        case 'Social Inbox':
          return plan && (plan.ai_inbox || plan.plan_name !== 'free')
        case 'Brand Brain':
          return plan && (plan.premium_ai_models || plan.plan_name !== 'free')
        case 'Integrations':
          return true // Feature flag already handles this
        default:
          return true
      }
    })
  }, [plan])

  // Memoize handlers to prevent re-creation
  const handleSidebarOpen = useCallback(() => {
    setSidebarOpen(true)
  }, [])

  const handleSidebarClose = useCallback(() => {
    setSidebarOpen(false)
  }, [])

  const handleUserMenuToggle = useCallback(() => {
    setUserMenuOpen((prev) => !prev)
  }, [])

  const handleUserMenuClose = useCallback(() => {
    setUserMenuOpen(false)
  }, [])

  const handleLogout = useCallback(() => {
    setUserMenuOpen(false)
    logout()
  }, [logout])

  // Load user settings on component mount
  useEffect(() => {
    const loadSettings = async () => {
      if (!isAuthenticated || !api) return

      try {
        const settings = await api.settings.get()
        setAutopilotMode(settings.enable_autonomous_mode || false)
        setSettingsLoaded(true)
      } catch (error) {
        console.error('Failed to load user settings:', error)
        setSettingsLoaded(true) // Still mark as loaded to prevent blocking UI
      }
    }

    loadSettings()
  }, [api, isAuthenticated])

  // Handle autonomous mode toggle
  const handleAutopilotToggle = useCallback(async () => {
    if (loadingAutopilot) return

    setLoadingAutopilot(true)
    const newMode = !autopilotMode

    try {
      await api.settings.update({ enable_autonomous_mode: newMode })
      setAutopilotMode(newMode)
      showSuccess(
        newMode
          ? '🚁 Full Autopilot Activated! Lily will now handle everything automatically.'
          : '👀 Review Mode Activated! Lily will ask for approval before posting.'
      )
    } catch (error) {
      showError('Failed to update autonomous mode settings')
      console.error('Autopilot toggle error:', error)
    } finally {
      setLoadingAutopilot(false)
    }
  }, [api, autopilotMode, loadingAutopilot, showSuccess, showError])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Mobile sidebar */}
      <div className={`relative z-50 lg:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div
          className="fixed inset-0 bg-gray-900/80 dark:bg-black/80"
          onClick={handleSidebarClose}
        />

        <div className="fixed inset-0 flex">
          <div className="relative mr-16 flex w-full max-w-xs flex-1">
            <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
              <button
                type="button"
                className="-m-2.5 p-2.5 focus:outline-none focus:ring-2 focus:ring-white"
                onClick={handleSidebarClose}
                aria-label="Close navigation menu"
              >
                <XMarkIcon className="h-6 w-6 text-white" aria-hidden="true" />
              </button>
            </div>

            <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white dark:bg-gray-900 px-6 pb-2">
              <div className="flex h-16 shrink-0 items-center">
                <h1
                  className="text-xl font-bold text-gray-900 dark:text-white"
                  role="banner"
                >
                  AI Social Media Manager
                </h1>
              </div>
              <nav
                className="flex flex-1 flex-col"
                role="navigation"
                aria-label="Main navigation"
              >
                <ul className="flex flex-1 flex-col gap-y-7">
                  <li>
                    <ul className="-mx-2 space-y-1" role="list">
                      {navigationItems.map((item) => (
                        <li key={item.name} role="listitem">
                          <Link
                            to={item.href}
                            className={classNames(
                              location.pathname === item.href
                                ? 'bg-gray-50 dark:bg-gray-800 text-indigo-600 dark:text-indigo-400'
                                : 'text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-50 dark:hover:bg-gray-800',
                              'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500'
                            )}
                            aria-current={
                              location.pathname === item.href
                                ? 'page'
                                : undefined
                            }
                          >
                            <item.icon
                              className={classNames(
                                location.pathname === item.href
                                  ? 'text-indigo-600 dark:text-indigo-400'
                                  : 'text-gray-400 dark:text-gray-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400',
                                'h-6 w-6 shrink-0'
                              )}
                              aria-hidden="true"
                            />
                            {item.name}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </li>
                </ul>
              </nav>
            </div>
          </div>
        </div>
      </div>

      {/* Static sidebar for desktop */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
        <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-6">
          <div className="flex h-16 shrink-0 items-center">
            <h1
              className="text-xl font-bold text-gray-900 dark:text-white"
              role="banner"
            >
              AI Social Media Manager
            </h1>
          </div>
          <nav
            className="flex flex-1 flex-col"
            role="navigation"
            aria-label="Main navigation"
          >
            <ul className="flex flex-1 flex-col gap-y-7">
              <li>
                <ul className="-mx-2 space-y-1" role="list">
                  {navigationItems.map((item) => (
                    <li key={item.name} role="listitem">
                      <Link
                        to={item.href}
                        className={classNames(
                          location.pathname === item.href
                            ? 'bg-gray-50 dark:bg-gray-800 text-indigo-600 dark:text-indigo-400'
                            : 'text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-50 dark:hover:bg-gray-800',
                          'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500'
                        )}
                        aria-current={
                          location.pathname === item.href ? 'page' : undefined
                        }
                      >
                        <item.icon
                          className={classNames(
                            location.pathname === item.href
                              ? 'text-indigo-600 dark:text-indigo-400'
                              : 'text-gray-400 dark:text-gray-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400',
                            'h-6 w-6 shrink-0'
                          )}
                          aria-hidden="true"
                        />
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      <div className="lg:pl-72">
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-gray-700 dark:text-gray-300 lg:hidden focus:outline-none focus:ring-2 focus:ring-blue-500"
            onClick={handleSidebarOpen}
            aria-label="Open navigation menu"
          >
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>

          <div className="h-6 w-px bg-gray-200 dark:bg-gray-700 lg:hidden" />

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="relative flex flex-1 items-center">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {navigation.find((item) => item.href === location.pathname)
                  ?.name || 'Dashboard'}
              </h1>
            </div>
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              {/* Usage Quota Indicators */}
              {limits && (
                <div className="hidden lg:flex items-center space-x-4 bg-gray-50 dark:bg-gray-800 rounded-lg px-3 py-2 border border-gray-200 dark:border-gray-600">
                  <div className="flex items-center space-x-2">
                    <ChartBarIcon
                      className="h-4 w-4 text-gray-500"
                      aria-hidden="true"
                    />
                    <div className="text-xs">
                      <span className="font-medium text-gray-700 dark:text-gray-300">
                        {limits.posts?.daily_limit -
                          (limits.posts?.used_today || 0)}
                        /{limits.posts?.daily_limit}
                      </span>
                      <span className="text-gray-500 dark:text-gray-400 ml-1">
                        posts today
                      </span>
                    </div>
                  </div>
                  {limits.images?.monthly_limit && (
                    <div className="flex items-center space-x-2 border-l border-gray-300 dark:border-gray-600 pl-3">
                      <div className="text-xs">
                        <span className="font-medium text-gray-700 dark:text-gray-300">
                          {limits.images.monthly_limit -
                            (limits.images.used_month || 0)}
                          /{limits.images.monthly_limit}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400 ml-1">
                          images
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Plan-Aware Autonomous Mode Toggle */}
              <PlanGate
                feature="enhanced_autopilot"
                fallback={
                  <div className="flex items-center space-x-3 bg-gray-100 dark:bg-gray-700 rounded-full px-4 py-2 border border-gray-300 dark:border-gray-600 opacity-60">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      Review Only
                    </span>
                    <div className="relative inline-flex h-5 w-9 items-center rounded-full bg-gray-300 dark:bg-gray-600">
                      <span className="inline-block h-3 w-3 transform rounded-full bg-white shadow-sm ml-1" />
                    </div>
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 line-through">
                      Autopilot
                    </span>
                  </div>
                }
              >
                <div className="flex items-center space-x-3 bg-gray-50 dark:bg-gray-800 rounded-full px-4 py-2 border border-gray-200 dark:border-gray-600">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                    Review
                  </span>
                  <button
                    onClick={handleAutopilotToggle}
                    disabled={loadingAutopilot}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                      autopilotMode ? 'bg-green-500' : 'bg-gray-300'
                    } ${loadingAutopilot ? 'opacity-50 cursor-not-allowed' : ''}`}
                    aria-label={
                      autopilotMode
                        ? 'Switch to Review Mode - Currently in Autopilot Mode'
                        : 'Switch to Autopilot Mode - Currently in Review Mode'
                    }
                    title={
                      autopilotMode
                        ? 'Switch to Review Mode'
                        : 'Switch to Autopilot Mode'
                    }
                    role="switch"
                    aria-checked={autopilotMode}
                    {...getButtonProps(
                      'toggle autopilot mode',
                      loadingAutopilot
                    )}
                  >
                    <motion.span
                      className="inline-block h-3 w-3 transform rounded-full bg-white shadow-sm"
                      animate={{ x: autopilotMode ? 20 : 4 }}
                      transition={{
                        type: 'spring',
                        stiffness: 500,
                        damping: 30,
                      }}
                    />
                  </button>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                    Autopilot
                  </span>
                </div>
              </PlanGate>

              <div
                className="flex items-center space-x-2"
                role="status"
                aria-label="Connection status"
              >
                <div
                  className="h-2 w-2 bg-green-400 rounded-full"
                  aria-hidden="true"
                ></div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Connected
                </span>
              </div>

              {/* Theme Toggle */}
              <ThemeToggle className="mr-2" />

              {/* Notification system */}
              <NotificationSystem />

              {/* User menu */}
              <div className="relative">
                <button
                  type="button"
                  className="flex items-center space-x-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md p-1"
                  onClick={handleUserMenuToggle}
                  aria-expanded={userMenuOpen}
                  aria-haspopup="menu"
                  aria-label={`User menu for ${user?.name || user?.email || 'user'}`}
                >
                  {user?.picture ? (
                    <img
                      className="h-8 w-8 rounded-full"
                      src={user.picture}
                      alt={getImageAltText(
                        'avatar',
                        user?.name || user?.email || 'User'
                      )}
                    />
                  ) : (
                    <div
                      className="h-8 w-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center"
                      aria-hidden="true"
                    >
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {user?.name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                      </span>
                    </div>
                  )}
                  <span className="hidden md:block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {user?.name || user?.email || 'User'}
                  </span>
                </button>

                {userMenuOpen && (
                  <div
                    className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-gray-800 py-1 shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5"
                    role="menu"
                    aria-orientation="vertical"
                    aria-labelledby="user-menu-button"
                  >
                    <div
                      className="px-4 py-2 text-sm text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-600"
                      role="menuitem"
                    >
                      <div className="font-medium">{user?.name || 'User'}</div>
                      <div className="text-gray-500 dark:text-gray-400">
                        {user?.email}
                      </div>
                      {plan && (
                        <div className="mt-1 text-xs">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                            {plan.display_name || plan.plan_name}
                          </span>
                        </div>
                      )}
                    </div>
                    <Link
                      to="/billing"
                      className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:bg-gray-100 dark:focus:bg-gray-700"
                      onClick={handleUserMenuClose}
                      role="menuitem"
                    >
                      <div className="flex items-center">
                        <CreditCardIcon
                          className="mr-2 h-4 w-4"
                          aria-hidden="true"
                        />
                        Billing & Plans
                      </div>
                    </Link>
                    <Link
                      to="/settings"
                      className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:bg-gray-100 dark:focus:bg-gray-700"
                      onClick={handleUserMenuClose}
                      role="menuitem"
                    >
                      <div className="flex items-center">
                        <Cog6ToothIcon
                          className="mr-2 h-4 w-4"
                          aria-hidden="true"
                        />
                        Settings
                      </div>
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="flex w-full items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:bg-gray-100 dark:focus:bg-gray-700"
                      role="menuitem"
                    >
                      <ArrowRightOnRectangleIcon
                        className="mr-2 h-4 w-4"
                        aria-hidden="true"
                      />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <main
          id="main-content"
          className="py-8 bg-gray-50 dark:bg-gray-900"
          role="main"
          aria-label="Main content"
        >
          <div className="px-4 sm:px-6 lg:px-8">
            {/* Usage notifications for limit warnings */}
            <div className="mb-6">
              <UsageNotifications />
            </div>

            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default React.memo(Layout)
