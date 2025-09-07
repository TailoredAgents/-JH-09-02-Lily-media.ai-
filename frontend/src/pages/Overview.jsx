import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  DocumentTextIcon,
  PlusIcon,
  SparklesIcon,
  CpuChipIcon,
  CalendarDaysIcon,
  CheckCircleIcon,
  ClockIcon,
  PhotoIcon,
  ArrowRightIcon,
  HeartIcon,
} from '@heroicons/react/24/outline'
import { useEnhancedApi } from '../hooks/useEnhancedApi'
import { useNotifications } from '../hooks/useNotifications'
import { usePlan } from '../contexts/PlanContext'
import { Link } from 'react-router-dom'
import PlanGate, { UsageLimitIndicator } from '../components/PlanGate'

const ContentCard = ({
  title,
  count,
  icon: Icon,
  color = 'blue',
  description,
  linkTo,
}) => {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-400',
    green: 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-400',
    purple:
      'text-purple-600 bg-purple-100 dark:bg-purple-900 dark:text-purple-400',
    orange:
      'text-orange-600 bg-orange-100 dark:bg-orange-900 dark:text-orange-400',
    gray: 'text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-400',
  }

  return (
    <Link to={linkTo} className="group">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow p-6 group-hover:border-blue-200 dark:group-hover:border-blue-600 border border-transparent">
        <div className="flex items-center justify-between">
          <div>
            <div
              className={`inline-flex p-3 rounded-lg ${colorClasses[color]} mb-4`}
            >
              <Icon className="h-6 w-6" />
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {count}
            </p>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
              {title}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {description}
            </p>
          </div>
          <ArrowRightIcon className="h-5 w-5 text-gray-400 dark:text-gray-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
        </div>
      </div>
    </Link>
  )
}

const QuickActionCard = ({
  title,
  description,
  icon: Icon,
  color = 'blue',
  action,
  disabled = false,
}) => {
  const colorClasses = {
    blue: 'bg-blue-600 hover:bg-blue-700 text-white',
    purple: 'bg-purple-600 hover:bg-purple-700 text-white',
    green: 'bg-green-600 hover:bg-green-700 text-white',
  }

  return (
    <button
      onClick={action}
      disabled={disabled}
      className={`${colorClasses[color]} rounded-lg p-6 text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full`}
    >
      <div className="flex items-center mb-3">
        <Icon className="h-8 w-8 mr-3" />
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      <p className="text-sm opacity-90">{description}</p>
    </button>
  )
}

export default function Overview() {
  const { api } = useEnhancedApi()
  const { showSuccess, showError } = useNotifications()
  const {
    plan,
    limits,
    hasFullAI,
    hasPremiumAI,
    canGenerateImage,
    canPostToday,
  } = usePlan()

  // Fetch content statistics
  const { data: contentStats, isLoading: contentLoading } = useQuery({
    queryKey: ['content-stats'],
    queryFn: async () => {
      const content = await api.content.getAll(1, 100)
      const aiGenerated = content.filter((item) => item.generated_by_ai).length
      const drafts = content.filter((item) => item.status === 'draft').length
      const scheduled = content.filter(
        (item) => item.status === 'scheduled'
      ).length
      const published = content.filter(
        (item) => item.status === 'published'
      ).length

      return {
        total: content.length,
        aiGenerated,
        drafts,
        scheduled,
        published,
      }
    },
    refetchInterval: 30 * 1000,
    retry: 2,
  })

  // Fetch upcoming content
  const { data: upcomingContent } = useQuery({
    queryKey: ['upcoming-content'],
    queryFn: () => api.content.getUpcoming(),
    retry: 2,
  })

  // Fetch memory stats for industry insights
  const { data: memoryStats } = useQuery({
    queryKey: ['memory-analytics'],
    queryFn: () => api.memory.getAnalytics(),
    retry: 2,
  })

  const handleGenerateAIContent = async () => {
    const prompt = window.prompt('Enter a prompt for AI content generation:')
    if (prompt && prompt.trim()) {
      try {
        // This would typically be handled by a mutation, but for demo:
        alert('Redirecting to Create Post page with AI generation...')
        window.location.href = '/create-post'
      } catch (error) {
        alert('Failed to generate content. Please try again.')
      }
    }
  }

  const handleScheduleContent = () => {
    window.location.href = '/calendar'
  }

  const handleManageContent = () => {
    window.location.href = '/content'
  }

  // Load user settings including autonomous mode
  const { data: userSettings } = useQuery({
    queryKey: ['user-settings'],
    queryFn: async () => {
      try {
        // Use the generic request method from apiService
        const response = await fetch(`${api.baseURL}/api/user-settings/`, {
          headers: {
            Authorization: `Bearer ${api.token}`,
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        return data
      } catch (error) {
        console.error('Failed to fetch user settings:', error)
        // Return default settings as fallback
        return {
          enable_autonomous_mode: false,
          content_frequency: 3,
          auto_response_enabled: false,
          brand_voice: 'professional',
          creativity_level: 0.7,
          enable_images: true,
          preferred_platforms: ['twitter', 'instagram'],
        }
      }
    },
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  })

  if (contentLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-32 bg-gray-300 rounded-lg"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-40 bg-gray-300 rounded-lg"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Lily's Introduction */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg p-8 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-6 mb-4">
              <div>
                <h1 className="text-4xl font-bold mb-2">👋 Hi, I'm Lily!</h1>
                <h2 className="text-2xl font-semibold mb-3 text-blue-100">
                  Your new Social Media Manager 😊
                </h2>
              </div>
            </div>
            <p className="text-blue-100 text-lg mb-2">
              I'm your AI Social Media Manager! I can research trends, create
              content, schedule posts, and manage your social presence with your
              guidance.
            </p>
            <div className="flex items-center space-x-4 text-sm text-blue-200">
              <span className="flex items-center">
                <span className="text-lg mr-1">🎯</span>
                Smart Content Creation
              </span>
              <span className="flex items-center">
                <span className="text-lg mr-1">⏱️</span>
                Saving you 10+ hours/week
              </span>
            </div>
            <div className="mt-4 flex items-center space-x-6 text-sm">
              <div>
                <span className="font-semibold">
                  {contentStats?.total || 0}
                </span>{' '}
                Total Content Created
              </div>
              <div>
                <span className="font-semibold">
                  {contentStats?.aiGenerated || 0}
                </span>{' '}
                Posts by Lily
              </div>
              <div>
                <span className="font-semibold">
                  {upcomingContent?.length || 0}
                </span>{' '}
                Ready to Publish
              </div>
            </div>
          </div>
          <div className="text-right">
            <Link
              to="/create-post"
              className="group inline-flex items-center px-8 py-4 bg-gradient-to-r from-white to-blue-50 hover:from-blue-50 hover:to-white text-blue-600 font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 border border-white border-opacity-50 backdrop-blur-sm"
            >
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg mr-3 group-hover:bg-blue-200 transition-colors duration-200">
                  <PlusIcon className="h-5 w-5 text-blue-600" />
                </div>
                <span className="text-lg">Let's Create Together</span>
                <svg
                  className="ml-2 h-5 w-5 transform group-hover:translate-x-1 transition-transform duration-200"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 8l4 4m0 0l-4 4m4-4H3"
                  />
                </svg>
              </div>
            </Link>
          </div>
        </div>
      </div>

      {/* Plan Status & Usage Limits */}
      <PlanGate showUpgradePrompt={false}>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Current Plan: {plan?.display_name || 'Free'}
            </h3>
            <Link
              to="/billing"
              className="text-blue-600 hover:text-blue-500 text-sm font-medium"
            >
              Manage Plan →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <PlanGate limit="posts" showUpgradePrompt={false}>
              <UsageLimitIndicator
                limitType="posts"
                className="bg-gray-50 dark:bg-gray-900 p-3 rounded"
              />
            </PlanGate>

            <PlanGate limit="images" showUpgradePrompt={false}>
              <UsageLimitIndicator
                limitType="images"
                className="bg-gray-50 dark:bg-gray-900 p-3 rounded"
              />
            </PlanGate>

            <PlanGate limit="social_profiles" showUpgradePrompt={false}>
              <UsageLimitIndicator
                limitType="social_profiles"
                className="bg-gray-50 dark:bg-gray-900 p-3 rounded"
              />
            </PlanGate>
          </div>
        </div>
      </PlanGate>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <PlanGate
          fallback={
            <div className="relative">
              <QuickActionCard
                title="Let Lily Create"
                description="Upgrade to unlock AI content creation"
                icon={SparklesIcon}
                color="purple"
                action={() => (window.location.href = '/billing')}
                disabled={!canPostToday()}
              />
              <div className="absolute inset-0 bg-gray-900/20 rounded-lg flex items-center justify-center">
                <div className="bg-white px-3 py-1 rounded-full text-xs font-medium text-gray-600">
                  Upgrade Required
                </div>
              </div>
            </div>
          }
          showUpgradePrompt={!hasFullAI()}
        >
          <QuickActionCard
            title="Let Lily Create"
            description="I'll craft engaging posts using the latest industry insights and trends"
            icon={SparklesIcon}
            color="purple"
            action={handleGenerateAIContent}
            disabled={!canPostToday()}
          />
        </PlanGate>

        <QuickActionCard
          title="Schedule Content"
          description="Plan and schedule your content across platforms"
          icon={CalendarDaysIcon}
          color="blue"
          action={handleScheduleContent}
        />
        <QuickActionCard
          title="Content Library"
          description="Browse and manage all the content I've created for you"
          icon={DocumentTextIcon}
          color="green"
          action={handleManageContent}
        />
      </div>

      {/* Content Statistics */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Content Overview
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <ContentCard
            title="Draft Content"
            count={contentStats?.drafts || 0}
            icon={DocumentTextIcon}
            color="gray"
            description="Ready for review and publishing"
            linkTo="/content?status=draft"
          />
          <ContentCard
            title="AI Generated"
            count={contentStats?.aiGenerated || 0}
            icon={SparklesIcon}
            color="purple"
            description="Created with artificial intelligence"
            linkTo="/content"
          />
          <ContentCard
            title="Scheduled"
            count={contentStats?.scheduled || 0}
            icon={ClockIcon}
            color="blue"
            description="Queued for automatic publishing"
            linkTo="/calendar"
          />
          <ContentCard
            title="Published"
            count={contentStats?.published || 0}
            icon={CheckCircleIcon}
            color="green"
            description="Successfully posted content"
            linkTo="/content?status=published"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upcoming Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Upcoming Content
          </h3>
          {upcomingContent && upcomingContent.length > 0 ? (
            <div className="space-y-3">
              {upcomingContent.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {item.title}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {item.platform} •{' '}
                      {new Date(item.scheduled_at).toLocaleDateString()}
                    </p>
                  </div>
                  {item.image_url && (
                    <PhotoIcon className="h-4 w-4 text-gray-400 ml-2" />
                  )}
                </div>
              ))}
              <Link
                to="/calendar"
                className="block text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 mt-3"
              >
                View all scheduled →
              </Link>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              No scheduled content. Start by creating some posts!
            </p>
          )}
        </div>

        {/* Lily's Capabilities */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            What I Can Do For You
          </h3>
          <div className="space-y-4">
            <div className="flex items-center">
              <CpuChipIcon className="h-5 w-5 text-purple-600 mr-3" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Industry Research
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  I stay up-to-date with the latest trends in your industry
                </p>
              </div>
              <span className="text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 px-2 py-1 rounded-full">
                Always On
              </span>
            </div>
            <div className="flex items-center">
              <SparklesIcon className="h-5 w-5 text-blue-600 mr-3" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Content Creation
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Professional posts tailored to your brand and audience
                </p>
              </div>
              <span className="text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 px-2 py-1 rounded-full">
                Ready
              </span>
            </div>
            <div className="flex items-center">
              <PhotoIcon className="h-5 w-5 text-orange-600 mr-3" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Visual Content
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Eye-catching images to complement your posts
                </p>
              </div>
              <span className="text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 px-2 py-1 rounded-full">
                Available
              </span>
            </div>
            <Link
              to="/create-post"
              className="block text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 mt-3"
            >
              Let's get started together →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
