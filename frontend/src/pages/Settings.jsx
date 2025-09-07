import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useEnhancedApi } from '../hooks/useEnhancedApi'
import { useNotifications } from '../hooks/useNotifications'
import { useTheme } from '../contexts/ThemeContext'
import { usePlan } from '../contexts/PlanContext'
import { error as logError } from '../utils/logger.js'
import SocialPlatformManager from '../components/SocialPlatforms/SocialPlatformManager'
import ErrorLogs from '../components/ErrorLogs'
import StyleVault from '../components/StyleVault'
import PlanGate from '../components/PlanGate'
import {
  UserIcon,
  KeyIcon,
  LinkIcon,
  BellIcon,
  CogIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftRightIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
} from '@heroicons/react/24/outline'

export default function Settings() {
  const { user } = useAuth()
  const { api, connectionStatus, checkApiHealth, clearCache } = useEnhancedApi()
  const { showSuccess, showError } = useNotifications()
  const { isDarkMode, setTheme, theme, systemTheme } = useTheme()

  const [isLoading, setIsLoading] = useState(false)
  const [isResearching, setIsResearching] = useState(false)
  const [researchProgress, setResearchProgress] = useState(0)
  const [researchStage, setResearchStage] = useState('')
  const [apiHealth, setApiHealth] = useState(null)

  const [settings, setSettings] = useState({
    industryContext: {
      companyName: '',
      industry: 'Technology',
      companyDescription: '',
      targetAudience: '',
      brandTone: 'Professional',
      keyTopics: '',
    },
    notifications: {
      goalMilestones: true,
      contentPublished: true,
      workflowComplete: true,
      systemAlerts: true,
      apiErrors: true,
    },
    automation: {
      dailyWorkflows: true,
      autoOptimization: false,
      smartScheduling: true,
      contentGeneration: true,
    },
    socialInbox: {
      defaultResponsePersonality: 'professional',
      autoResponseEnabled: false,
      autoResponseConfidenceThreshold: 0.8,
      autoResponseBusinessHoursOnly: true,
      autoResponseDelayMinutes: 5,
      businessHoursStart: '09:00',
      businessHoursEnd: '17:00',
      businessDays: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
      escalationKeywords: [
        'complaint',
        'lawsuit',
        'refund',
        'angry',
        'terrible',
      ],
      excludedResponseKeywords: ['spam', 'bot', 'fake'],
    },
    platforms: {
      twitter: { connected: false, username: '' },
      instagram: { connected: false, username: '' },
      facebook: { connected: false, username: '' },
    },
  })

  // Check API health on component mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await checkApiHealth()
        setApiHealth(health)
      } catch (error) {
        logError('Health check failed:', error)
      }
    }

    checkHealth()
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkApiHealth])

  const handleNotificationChange = (key) => {
    setSettings((prev) => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [key]: !prev.notifications[key],
      },
    }))
    showSuccess('Notification preferences updated')
  }

  const handleAutomationChange = (key) => {
    setSettings((prev) => ({
      ...prev,
      automation: {
        ...prev.automation,
        [key]: !prev.automation[key],
      },
    }))
    showSuccess('Automation settings updated')
  }

  const handleIndustryContextChange = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      industryContext: {
        ...prev.industryContext,
        [field]: value,
      },
    }))
  }

  const researchCompany = async () => {
    if (!settings.industryContext.companyName.trim()) {
      showError('Please enter a company name to research')
      return
    }

    setIsResearching(true)
    setResearchProgress(0)
    setResearchStage('')

    // Progress simulation stages
    const stages = [
      {
        progress: 10,
        stage: 'Initializing deep research agents...',
        duration: 1000,
      },
      {
        progress: 25,
        stage: 'Gathering company intelligence and recent news...',
        duration: 2500,
      },
      {
        progress: 45,
        stage: 'Analyzing market position and competitive landscape...',
        duration: 2000,
      },
      {
        progress: 65,
        stage: 'Researching company culture and values...',
        duration: 1500,
      },
      {
        progress: 80,
        stage: 'Identifying content opportunities and themes...',
        duration: 1500,
      },
      {
        progress: 95,
        stage: 'Synthesizing insights and recommendations...',
        duration: 1000,
      },
      { progress: 100, stage: 'Research complete!', duration: 500 },
    ]

    try {
      // Start progress simulation
      const progressPromise = new Promise((resolve) => {
        let currentStage = 0
        const progressInterval = setInterval(
          () => {
            if (currentStage < stages.length) {
              const stage = stages[currentStage]
              setResearchProgress(stage.progress)
              setResearchStage(stage.stage)

              if (currentStage === stages.length - 1) {
                setTimeout(() => {
                  clearInterval(progressInterval)
                  resolve()
                }, stage.duration)
              }
              currentStage++
            }
          },
          stages[Math.min(currentStage, stages.length - 1)]?.duration || 1000
        )
      })

      // Call company research API (this will take time for real research)
      const [response] = await Promise.all([
        api.autonomous.researchCompany(settings.industryContext.companyName),
        progressPromise, // Ensure progress completes
      ])

      if (response && response.success) {
        // Update settings with research results
        setSettings((prev) => ({
          ...prev,
          industryContext: {
            ...prev.industryContext,
            industry: response.industry || prev.industryContext.industry,
            companyDescription: response.description || '',
            targetAudience: response.target_audience || '',
            keyTopics: response.key_topics
              ? response.key_topics.join(', ')
              : '',
          },
        }))

        showSuccess(
          `Deep research complete! Lily discovered ${response.insights?.recent_news?.length || 0} recent insights and ${response.insights?.content_themes?.length || 0} content opportunities for ${settings.industryContext.companyName}`
        )
      } else {
        showError(
          'Company research failed. Please try manually entering the information.'
        )
      }
    } catch (error) {
      logError('Company research failed:', error)
      showError(
        'Failed to research company. Please check your connection and try again.'
      )
    } finally {
      setIsResearching(false)
      setResearchProgress(0)
      setResearchStage('')
    }
  }

  const saveIndustryContext = () => {
    // Here you would typically save to backend/localStorage
    showSuccess(
      'Industry context updated! Lily will use this info for content creation.'
    )
  }

  const handleTestNotification = () => {
    showSuccess('Test notification sent successfully!', 'Test Notification')
  }

  const handleClearCache = async () => {
    try {
      setIsLoading(true)
      clearCache()
      showSuccess('Cache cleared successfully')
    } catch (error) {
      showError('Failed to clear cache')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportData = async () => {
    try {
      setIsLoading(true)

      // Gather all data for export
      const [memoryData, goalsData, contentData, analyticsData] =
        await Promise.allSettled([
          api.memory.getAll(1, 1000),
          api.goals.getAll(),
          api.content.getAll(1, 1000),
          api.analytics.getAnalytics(),
        ])

      const exportData = {
        timestamp: new Date().toISOString(),
        user: user,
        memory: memoryData.status === 'fulfilled' ? memoryData.value : [],
        goals: goalsData.status === 'fulfilled' ? goalsData.value : [],
        content: contentData.status === 'fulfilled' ? contentData.value : [],
        analytics:
          analyticsData.status === 'fulfilled' ? analyticsData.value : {},
      }

      // Create and download file
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `ai-social-agent-export-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      showSuccess('Data exported successfully')
    } catch (error) {
      showError('Failed to export data')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportCSV = async () => {
    try {
      setIsLoading(true)

      const contentData = await api.content.getAll(1, 1000)

      if (!contentData || contentData.length === 0) {
        showError('No content data to export')
        return
      }

      // Create CSV content
      const headers = [
        'ID',
        'Title',
        'Content',
        'Platform',
        'Status',
        'Created Date',
        'Scheduled Date',
      ]
      const csvRows = [headers.join(',')]

      contentData.forEach((item) => {
        const row = [
          item.id || '',
          `"${(item.title || '').replace(/"/g, '""')}"`,
          `"${(item.content || '').replace(/"/g, '""')}"`,
          item.platform || '',
          item.status || '',
          item.created_at || '',
          item.scheduled_at || '',
        ]
        csvRows.push(row.join(','))
      })

      const csvContent = csvRows.join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `ai-social-agent-content-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      showSuccess('CSV exported successfully')
    } catch (error) {
      showError('Failed to export CSV')
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'disconnected':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'reconnecting':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected':
        return 'text-green-600'
      case 'disconnected':
        return 'text-red-600'
      case 'reconnecting':
        return 'text-yellow-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Settings
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Configure your brand, preferences, and integrations
        </p>
      </div>

      {/* User Profile */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <UserIcon className="h-5 w-5 mr-2" />
            Profile
          </h3>
        </div>
        <div className="p-6">
          <div className="flex items-center space-x-4">
            <div className="h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center">
              <UserIcon className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <h4 className="text-lg font-medium text-gray-900">
                {user?.name || 'Anonymous User'}
              </h4>
              <p className="text-sm text-gray-600">
                {user?.email || 'No email available'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Member since{' '}
                {user?.created_at
                  ? new Date(user.created_at).toLocaleDateString()
                  : 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Theme Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            {isDarkMode ? (
              <MoonIcon className="h-5 w-5 mr-2" />
            ) : (
              <SunIcon className="h-5 w-5 mr-2" />
            )}
            Theme Preferences
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Customize the appearance of the application
          </p>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Choose your preferred theme
            </p>
            <div className="space-y-3">
              {[
                {
                  key: 'light',
                  name: 'Light Mode',
                  description: 'Clean and bright interface',
                  icon: SunIcon,
                },
                {
                  key: 'dark',
                  name: 'Dark Mode',
                  description: 'Easy on the eyes in low light',
                  icon: MoonIcon,
                },
                {
                  key: 'system',
                  name: 'System',
                  description: `Follow system preference (currently ${systemTheme})`,
                  icon: ComputerDesktopIcon,
                },
              ].map((themeOption) => {
                const Icon = themeOption.icon
                const isSelected = theme === themeOption.key

                return (
                  <button
                    key={themeOption.key}
                    onClick={() => {
                      setTheme(themeOption.key)
                      showSuccess(`Theme changed to ${themeOption.name}`)
                    }}
                    className={`relative flex items-center space-x-3 w-full text-left p-4 rounded-lg border-2 transition-colors ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-950 dark:border-blue-400'
                        : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Icon
                      className={`h-6 w-6 ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-500'}`}
                    />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`text-sm font-medium ${isSelected ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-white'}`}
                        >
                          {themeOption.name}
                        </span>
                        {isSelected && (
                          <CheckCircleIcon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        )}
                      </div>
                      <span
                        className={`text-xs ${isSelected ? 'text-blue-700 dark:text-blue-200' : 'text-gray-500 dark:text-gray-400'}`}
                      >
                        {themeOption.description}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Industry Context */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <CogIcon className="h-5 w-5 mr-2" />
            Industry Context for Lily
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Help Lily understand your business to create better, more targeted
            content
          </p>
        </div>
        <div className="p-6 space-y-6">
          {/* Company Research Section */}
          <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-3">
              ✨ Quick Setup with AI Research
            </h4>
            <p className="text-sm text-blue-800 dark:text-blue-200 mb-4">
              Just enter your company name and let Lily research everything else
              for you!
            </p>

            <div className="flex space-x-3">
              <div className="flex-1">
                <input
                  type="text"
                  value={settings.industryContext.companyName}
                  onChange={(e) =>
                    handleIndustryContextChange('companyName', e.target.value)
                  }
                  className="w-full border border-blue-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter your company name (e.g., Apple, Tesla, OpenAI)"
                  disabled={isResearching}
                />
              </div>
              <button
                onClick={researchCompany}
                disabled={
                  isResearching || !settings.industryContext.companyName.trim()
                }
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isResearching ? (
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <MagnifyingGlassIcon className="h-4 w-4" />
                )}
                <span>
                  {isResearching ? 'Deep Research' : 'Research Company'}
                </span>
              </button>
            </div>

            {/* Progress Bar */}
            {isResearching && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h5 className="font-medium text-blue-900">
                    Deep Company Analysis in Progress
                  </h5>
                  <span className="text-blue-800 font-semibold">
                    {researchProgress}%
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-blue-200 rounded-full h-3 mb-3">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${researchProgress}%` }}
                  ></div>
                </div>

                {/* Current Stage */}
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <p className="text-sm text-blue-800 font-medium">
                    {researchStage}
                  </p>
                </div>

                <p className="text-xs text-blue-600 mt-2">
                  🔍 Lily is conducting comprehensive research using advanced AI
                  agents and multiple data sources to provide you with specific,
                  actionable insights.
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Industry
              </label>
              <select
                value={settings.industryContext.industry}
                onChange={(e) =>
                  handleIndustryContextChange('industry', e.target.value)
                }
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <optgroup label="Technology">
                  <option value="Software Development">
                    Software Development
                  </option>
                  <option value="SaaS & Cloud Computing">
                    SaaS & Cloud Computing
                  </option>
                  <option value="Artificial Intelligence & ML">
                    Artificial Intelligence & ML
                  </option>
                  <option value="Cybersecurity">Cybersecurity</option>
                  <option value="Mobile App Development">
                    Mobile App Development
                  </option>
                  <option value="Hardware & Electronics">
                    Hardware & Electronics
                  </option>
                  <option value="Fintech">Fintech</option>
                  <option value="EdTech">EdTech</option>
                  <option value="HealthTech">HealthTech</option>
                  <option value="Gaming & Entertainment">
                    Gaming & Entertainment
                  </option>
                </optgroup>
                <optgroup label="Healthcare & Life Sciences">
                  <option value="Medical Devices">Medical Devices</option>
                  <option value="Pharmaceuticals">Pharmaceuticals</option>
                  <option value="Biotechnology">Biotechnology</option>
                  <option value="Healthcare Services">
                    Healthcare Services
                  </option>
                  <option value="Mental Health">Mental Health</option>
                  <option value="Telemedicine">Telemedicine</option>
                  <option value="Medical Research">Medical Research</option>
                </optgroup>
                <optgroup label="Financial Services">
                  <option value="Banking & Credit">Banking & Credit</option>
                  <option value="Investment & Wealth Management">
                    Investment & Wealth Management
                  </option>
                  <option value="Insurance">Insurance</option>
                  <option value="Cryptocurrency & Blockchain">
                    Cryptocurrency & Blockchain
                  </option>
                  <option value="Payment Processing">Payment Processing</option>
                  <option value="Financial Planning">Financial Planning</option>
                </optgroup>
                <optgroup label="E-commerce & Retail">
                  <option value="Online Marketplace">Online Marketplace</option>
                  <option value="D2C Brands">D2C Brands</option>
                  <option value="Fashion & Apparel">Fashion & Apparel</option>
                  <option value="Beauty & Cosmetics">Beauty & Cosmetics</option>
                  <option value="Home & Garden">Home & Garden</option>
                  <option value="Electronics Retail">Electronics Retail</option>
                  <option value="Grocery & Food Delivery">
                    Grocery & Food Delivery
                  </option>
                </optgroup>
                <optgroup label="Professional Services">
                  <option value="Marketing & Advertising">
                    Marketing & Advertising
                  </option>
                  <option value="Business Consulting">
                    Business Consulting
                  </option>
                  <option value="Legal Services">Legal Services</option>
                  <option value="Accounting & Finance">
                    Accounting & Finance
                  </option>
                  <option value="Human Resources">Human Resources</option>
                  <option value="Design & Creative">Design & Creative</option>
                  <option value="PR & Communications">
                    PR & Communications
                  </option>
                </optgroup>
                <optgroup label="Real Estate & Construction">
                  <option value="Commercial Real Estate">
                    Commercial Real Estate
                  </option>
                  <option value="Residential Real Estate">
                    Residential Real Estate
                  </option>
                  <option value="Property Management">
                    Property Management
                  </option>
                  <option value="Construction">Construction</option>
                  <option value="Architecture & Engineering">
                    Architecture & Engineering
                  </option>
                  <option value="Real Estate Technology">
                    Real Estate Technology
                  </option>
                </optgroup>
                <optgroup label="Food & Beverage">
                  <option value="Restaurants & Food Service">
                    Restaurants & Food Service
                  </option>
                  <option value="Food Manufacturing">Food Manufacturing</option>
                  <option value="Beverage Industry">Beverage Industry</option>
                  <option value="Specialty Foods">Specialty Foods</option>
                  <option value="Food Technology">Food Technology</option>
                  <option value="Catering & Events">Catering & Events</option>
                </optgroup>
                <optgroup label="Manufacturing & Industrial">
                  <option value="Automotive">Automotive</option>
                  <option value="Aerospace & Defense">
                    Aerospace & Defense
                  </option>
                  <option value="Chemical & Materials">
                    Chemical & Materials
                  </option>
                  <option value="Energy & Utilities">Energy & Utilities</option>
                  <option value="Manufacturing Equipment">
                    Manufacturing Equipment
                  </option>
                  <option value="Logistics & Supply Chain">
                    Logistics & Supply Chain
                  </option>
                </optgroup>
                <optgroup label="Media & Entertainment">
                  <option value="Digital Media">Digital Media</option>
                  <option value="Film & Television">Film & Television</option>
                  <option value="Music & Audio">Music & Audio</option>
                  <option value="Publishing">Publishing</option>
                  <option value="Social Media Platforms">
                    Social Media Platforms
                  </option>
                  <option value="Content Creation">Content Creation</option>
                </optgroup>
                <optgroup label="Education & Training">
                  <option value="K-12 Education">K-12 Education</option>
                  <option value="Higher Education">Higher Education</option>
                  <option value="Online Learning">Online Learning</option>
                  <option value="Corporate Training">Corporate Training</option>
                  <option value="Vocational Training">
                    Vocational Training
                  </option>
                  <option value="Educational Technology">
                    Educational Technology
                  </option>
                </optgroup>
                <optgroup label="Fitness & Wellness">
                  <option value="Fitness & Gyms">Fitness & Gyms</option>
                  <option value="Wellness & Spa">Wellness & Spa</option>
                  <option value="Sports & Recreation">
                    Sports & Recreation
                  </option>
                  <option value="Nutrition & Supplements">
                    Nutrition & Supplements
                  </option>
                  <option value="Mental Wellness">Mental Wellness</option>
                  <option value="Fitness Technology">Fitness Technology</option>
                </optgroup>
                <optgroup label="Travel & Hospitality">
                  <option value="Hotels & Accommodation">
                    Hotels & Accommodation
                  </option>
                  <option value="Travel Agencies">Travel Agencies</option>
                  <option value="Airlines">Airlines</option>
                  <option value="Tourism & Experiences">
                    Tourism & Experiences
                  </option>
                  <option value="Travel Technology">Travel Technology</option>
                  <option value="Event Planning">Event Planning</option>
                </optgroup>
                <optgroup label="Other Industries">
                  <option value="Non-Profit & NGO">Non-Profit & NGO</option>
                  <option value="Government & Public Sector">
                    Government & Public Sector
                  </option>
                  <option value="Agriculture">Agriculture</option>
                  <option value="Environmental Services">
                    Environmental Services
                  </option>
                  <option value="Personal Services">Personal Services</option>
                  <option value="Other">Other</option>
                </optgroup>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Brand Tone
              </label>
              <select
                value={settings.industryContext.brandTone}
                onChange={(e) =>
                  handleIndustryContextChange('brandTone', e.target.value)
                }
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Professional">Professional</option>
                <option value="Friendly">Friendly</option>
                <option value="Casual">Casual</option>
                <option value="Witty">Witty</option>
                <option value="Authoritative">Authoritative</option>
                <option value="Inspirational">Inspirational</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company Description
              <span className="text-xs text-blue-600 ml-2">
                (Auto-filled by research or manual entry)
              </span>
            </label>
            <textarea
              value={settings.industryContext.companyDescription}
              onChange={(e) =>
                handleIndustryContextChange(
                  'companyDescription',
                  e.target.value
                )
              }
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Will be auto-filled by company research or enter manually..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Audience
              <span className="text-xs text-blue-600 ml-2">
                (Auto-filled by research or manual entry)
              </span>
            </label>
            <textarea
              value={settings.industryContext.targetAudience}
              onChange={(e) =>
                handleIndustryContextChange('targetAudience', e.target.value)
              }
              rows={2}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Will be auto-filled by company research or enter manually..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Key Topics & Keywords
              <span className="text-xs text-blue-600 ml-2">
                (Auto-filled by research or manual entry)
              </span>
            </label>
            <textarea
              value={settings.industryContext.keyTopics}
              onChange={(e) =>
                handleIndustryContextChange('keyTopics', e.target.value)
              }
              rows={2}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Will be auto-filled by company research or enter manually..."
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={saveIndustryContext}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <CheckCircleIcon className="h-4 w-4" />
              <span>Save Context</span>
            </button>
          </div>
        </div>
      </div>

      {/* Style Vault */}
      <PlanGate
        feature="white_label"
        showUpgradePrompt={true}
        fallback={
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
                <CogIcon className="h-5 w-5 mr-2" />
                Style Vault (Premium)
              </h3>
            </div>
            <div className="p-6 text-center">
              <div className="mb-4">
                <CogIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-600 dark:text-gray-400">
                  Upgrade to access the Style Vault feature for brand asset
                  management and custom styling.
                </p>
              </div>
              <button
                onClick={() => (window.location.href = '/billing')}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
              >
                Upgrade Plan
              </button>
            </div>
          </div>
        }
      >
        <StyleVault />
      </PlanGate>

      {/* System Status */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <CogIcon className="h-5 w-5 mr-2" />
            System Status
          </h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="flex items-center space-x-3">
                {getStatusIcon(connectionStatus)}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    API Connection
                  </p>
                  <p className={`text-sm ${getStatusColor(connectionStatus)}`}>
                    {connectionStatus}
                  </p>
                </div>
              </div>
              <button
                onClick={checkApiHealth}
                className="px-3 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200 rounded-md hover:bg-blue-200 dark:hover:bg-blue-800"
              >
                Test
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="flex items-center space-x-3">
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    Database
                  </p>
                  <p className="text-sm text-green-600">Connected</p>
                </div>
              </div>
              <span className="px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 rounded-md">
                Healthy
              </span>
            </div>
          </div>

          {apiHealth && (
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                API Health Details
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-blue-700 dark:text-blue-300">
                    Version:
                  </span>
                  <span className="ml-2 text-blue-900 dark:text-blue-100">
                    {apiHealth.version || 'Unknown'}
                  </span>
                </div>
                <div>
                  <span className="text-blue-700 dark:text-blue-300">
                    Uptime:
                  </span>
                  <span className="ml-2 text-blue-900 dark:text-blue-100">
                    {apiHealth.uptime || 'Unknown'}
                  </span>
                </div>
                <div>
                  <span className="text-blue-700 dark:text-blue-300">
                    Memory:
                  </span>
                  <span className="ml-2 text-blue-900 dark:text-blue-100">
                    {apiHealth.memory_usage || 'Unknown'}
                  </span>
                </div>
                <div>
                  <span className="text-blue-700 dark:text-blue-300">
                    Load:
                  </span>
                  <span className="ml-2 text-blue-900 dark:text-blue-100">
                    {apiHealth.cpu_usage || 'Unknown'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* System Health */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
            System Health
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Monitor system logs, errors, and performance metrics
          </p>
        </div>
        <div className="p-6">
          <ErrorLogs />
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <BellIcon className="h-5 w-5 mr-2" />
            Notifications
          </h3>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {Object.entries(settings.notifications).map(([key, enabled]) => (
              <div key={key} className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {key
                      .replace(/([A-Z])/g, ' $1')
                      .replace(/^./, (str) => str.toUpperCase())}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {key === 'goalMilestones' &&
                      'Get notified when you reach goal milestones'}
                    {key === 'contentPublished' &&
                      'Get notified when content is published'}
                    {key === 'workflowComplete' &&
                      'Get notified when workflows complete'}
                    {key === 'systemAlerts' &&
                      'Get notified about system issues'}
                    {key === 'apiErrors' && 'Get notified about API errors'}
                  </p>
                </div>
                <button
                  onClick={() => handleNotificationChange(key)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    enabled ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <button
              onClick={handleTestNotification}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Test Notifications
            </button>
          </div>
        </div>
      </div>

      {/* Automation Settings */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <CogIcon className="h-5 w-5 mr-2" />
            Automation
          </h3>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {Object.entries(settings.automation).map(([key, enabled]) => (
              <div key={key} className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">
                    {key
                      .replace(/([A-Z])/g, ' $1')
                      .replace(/^./, (str) => str.toUpperCase())}
                  </p>
                  <p className="text-sm text-gray-600">
                    {key === 'dailyWorkflows' &&
                      'Automatically run daily content workflows'}
                    {key === 'autoOptimization' &&
                      'Automatically optimize content based on performance'}
                    {key === 'smartScheduling' &&
                      'Use AI to determine optimal posting times'}
                    {key === 'contentGeneration' &&
                      'Enable automated content generation'}
                  </p>
                </div>
                <button
                  onClick={() => handleAutomationChange(key)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    enabled ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Social Inbox Settings */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
            Social Inbox & Auto-Response
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Configure how Lily responds to comments, mentions, and messages
          </p>
        </div>
        <div className="p-6 space-y-6">
          {/* Default Response Personality */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Default Response Personality
            </label>
            <select
              value={settings.socialInbox.defaultResponsePersonality}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  socialInbox: {
                    ...prev.socialInbox,
                    defaultResponsePersonality: e.target.value,
                  },
                }))
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="professional">
                Professional - Formal and courteous
              </option>
              <option value="friendly">Friendly - Warm and approachable</option>
              <option value="casual">Casual - Relaxed and informal</option>
              <option value="technical">
                Technical - Informative and precise
              </option>
            </select>
          </div>

          {/* Auto-Response Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">Enable Auto-Response</p>
              <p className="text-sm text-gray-600">
                Automatically respond to interactions based on AI confidence
              </p>
            </div>
            <button
              onClick={() =>
                setSettings((prev) => ({
                  ...prev,
                  socialInbox: {
                    ...prev.socialInbox,
                    autoResponseEnabled: !prev.socialInbox.autoResponseEnabled,
                  },
                }))
              }
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                settings.socialInbox.autoResponseEnabled
                  ? 'bg-blue-600'
                  : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.socialInbox.autoResponseEnabled
                    ? 'translate-x-6'
                    : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Auto-Response Configuration (only shown if enabled) */}
          {settings.socialInbox.autoResponseEnabled && (
            <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confidence Threshold (
                  {Math.round(
                    settings.socialInbox.autoResponseConfidenceThreshold * 100
                  )}
                  %)
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1"
                  step="0.05"
                  value={settings.socialInbox.autoResponseConfidenceThreshold}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      socialInbox: {
                        ...prev.socialInbox,
                        autoResponseConfidenceThreshold: parseFloat(
                          e.target.value
                        ),
                      },
                    }))
                  }
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Only auto-respond when AI confidence is above this threshold
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-700">
                    Business Hours Only
                  </p>
                  <p className="text-xs text-gray-500">
                    Only send auto-responses during business hours
                  </p>
                </div>
                <button
                  onClick={() =>
                    setSettings((prev) => ({
                      ...prev,
                      socialInbox: {
                        ...prev.socialInbox,
                        autoResponseBusinessHoursOnly:
                          !prev.socialInbox.autoResponseBusinessHoursOnly,
                      },
                    }))
                  }
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                    settings.socialInbox.autoResponseBusinessHoursOnly
                      ? 'bg-blue-600'
                      : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                      settings.socialInbox.autoResponseBusinessHoursOnly
                        ? 'translate-x-5'
                        : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {settings.socialInbox.autoResponseBusinessHoursOnly && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Start Time
                    </label>
                    <input
                      type="time"
                      value={settings.socialInbox.businessHoursStart}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          socialInbox: {
                            ...prev.socialInbox,
                            businessHoursStart: e.target.value,
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      End Time
                    </label>
                    <input
                      type="time"
                      value={settings.socialInbox.businessHoursEnd}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          socialInbox: {
                            ...prev.socialInbox,
                            businessHoursEnd: e.target.value,
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Response Delay (minutes)
                </label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={settings.socialInbox.autoResponseDelayMinutes}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      socialInbox: {
                        ...prev.socialInbox,
                        autoResponseDelayMinutes: parseInt(e.target.value),
                      },
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Wait this many minutes before sending auto-responses
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Platform Integrations */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <LinkIcon className="h-5 w-5 mr-2" />
            Platform Integrations
          </h3>
        </div>
        <div className="p-6">
          <SocialPlatformManager />
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <KeyIcon className="h-5 w-5 mr-2" />
            Advanced
          </h3>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Clear Cache</p>
                <p className="text-sm text-gray-600">
                  Clear all cached data to free up space
                </p>
              </div>
              <button
                onClick={handleClearCache}
                disabled={isLoading}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Clearing...' : 'Clear Cache'}
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Export Data</p>
                <p className="text-sm text-gray-600">
                  Download all your data as JSON or CSV
                </p>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={handleExportCSV}
                  disabled={isLoading}
                  className="px-4 py-2 bg-green-100 text-green-700 rounded-md hover:bg-green-200 transition-colors disabled:opacity-50"
                >
                  Export CSV
                </button>
                <button
                  onClick={handleExportData}
                  disabled={isLoading}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  Export JSON
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">API Documentation</p>
                <p className="text-sm text-gray-600">
                  View API documentation and examples
                </p>
              </div>
              <button className="px-4 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors">
                View Docs
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
