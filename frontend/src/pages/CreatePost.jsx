import { useState, useEffect } from 'react'
import { useEnhancedApi } from '../hooks/useEnhancedApi'
import { useNotifications } from '../hooks/useNotifications'
import { usePlan } from '../contexts/PlanContext'
import { error as logError } from '../utils/logger.js'
import ProgressBar from '../components/ProgressBar'
import RealtimeContentPreview from '../components/RealtimeContentPreview'
import PlanGate, { UsageLimitIndicator } from '../components/PlanGate'
import {
  PhotoIcon,
  DocumentTextIcon,
  SparklesIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

const platforms = [
  { value: 'twitter', label: 'Twitter', maxLength: 280 },
  { value: 'instagram', label: 'Instagram', maxLength: 2200 },
  { value: 'facebook', label: 'Facebook', maxLength: 63206 },
]

export default function CreatePost() {
  const { api } = useEnhancedApi()
  const { showSuccess, showError, showProgress } = useNotifications()
  const { canGenerateImage, canPostToday, limits } = usePlan()

  const [formData, setFormData] = useState({
    title: '',
    content: '',
    platform: 'twitter',
    tags: [],
  })

  const [isGenerating, setIsGenerating] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [generatedImage, setGeneratedImage] = useState(null)
  const [imagePrompt, setImagePrompt] = useState('')
  const [industryContext, setIndustryContext] = useState('')
  const [showResearchPanel, setShowResearchPanel] = useState(false)
  const [researchData, setResearchData] = useState(null)
  const [generateImageWithContent, setGenerateImageWithContent] = useState(true) // Default to true
  const [isResearching, setIsResearching] = useState(false)
  const [contentGenerationProgress, setContentGenerationProgress] =
    useState(false)
  const [imageGenerationProgress, setImageGenerationProgress] = useState(false)
  const [specificInstructions, setSpecificInstructions] = useState('')
  const [uploadedImage, setUploadedImage] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [imageSource, setImageSource] = useState('generate') // 'generate' or 'upload'

  const selectedPlatform = platforms.find((p) => p.value === formData.platform)

  useEffect(() => {
    // Auto-conduct industry research when component mounts
    conductIndustryResearch()
  }, [])

  const conductIndustryResearch = async () => {
    setIsResearching(true)
    try {
      // Get settings from localStorage to use for personalized research
      const savedSettings = localStorage.getItem('userSettings')
      const settings = savedSettings ? JSON.parse(savedSettings) : null
      const industryContext = settings?.industryContext

      console.log('Using industry context from settings:', industryContext) // Debug log

      // If we have company name, do personalized research
      if (industryContext?.companyName?.trim()) {
        console.log(
          'Conducting personalized research for:',
          industryContext.companyName
        )

        // Call personalized research API
        const response = await api.autonomous.researchCompany(
          industryContext.companyName
        )

        if (response && response.success) {
          const researchData = {
            industry: response.industry || industryContext.industry || 'N/A',
            trends: [], // Will be populated from insights
            keyTopics: industryContext.keyTopics
              ? industryContext.keyTopics.split(',').map((t) => t.trim())
              : [],
            contentSuggestions: [],
            competitorInsights: [],
          }

          // Extract insights from the response
          const insights = response.insights || {}
          if (insights.content_themes) {
            researchData.contentSuggestions = insights.content_themes
              .map((theme) => theme.content_opportunity || theme.insight)
              .filter(Boolean)
          }
          if (insights.recent_news) {
            researchData.competitorInsights = insights.recent_news
              .map((news) => news.insight)
              .filter(Boolean)
          }

          setResearchData(researchData)
          setIndustryContext(
            `Based on research for ${industryContext.companyName} in ${researchData.industry}`
          )

          console.log('Personalized research data:', researchData) // Debug log
        } else {
          throw new Error('Company research failed')
        }
      } else {
        // Fallback to generic industry research if no company name
        console.log('No company name found, using generic research')
        const response = await api.autonomous.getLatestResearch()

        const researchData = {
          industry:
            industryContext?.industry ||
            response.industry ||
            'AI Agent Products',
          trends: Array.isArray(response.trends) ? response.trends : [],
          keyTopics: industryContext?.keyTopics
            ? industryContext.keyTopics.split(',').map((t) => t.trim())
            : [],
          contentSuggestions: Array.isArray(response.content_opportunities)
            ? response.content_opportunities
            : [],
          competitorInsights: Array.isArray(response.insights)
            ? response.insights
            : [],
        }

        setResearchData(researchData)
        setIndustryContext(
          `Based on current trends in ${researchData.industry}`
        )
      }
    } catch (error) {
      logError('Research failed:', error)
      showError('Failed to conduct industry research')
      // Set empty state
      setResearchData({
        industry: 'N/A',
        trends: [],
        keyTopics: [],
        contentSuggestions: [],
        competitorInsights: [],
      })
      setIndustryContext('No research data available')
    } finally {
      setIsResearching(false)
    }
  }

  const handleChange = (field, value) => {
    setFormData((prev) => ({
      ...(prev || {}),
      [field]: value,
    }))
  }

  const generateAIContent = async () => {
    setIsGenerating(true)
    setContentGenerationProgress(true)

    // Show Lily's initial message
    showProgress('Let me focus and create something amazing for you! 😊', null)

    try {
      // Phase 1: Generate Caption First
      showProgress('Creating your caption with industry insights... ✍️', null)

      // Step 1: Get company research data for enhanced context using settings
      let companyResearchData = null
      try {
        // Get company name from settings
        const savedSettings = localStorage.getItem('userSettings')
        const settings = savedSettings ? JSON.parse(savedSettings) : null
        const companyName = settings?.industryContext?.companyName?.trim()

        if (companyName) {
          console.log(
            'Using company from settings for content generation:',
            companyName
          )
          const researchResponse =
            await api.autonomous.researchCompany(companyName)
          if (researchResponse && researchResponse.success) {
            companyResearchData = researchResponse
          }
        } else {
          console.log(
            'No company name in settings, skipping personalized research'
          )
        }
      } catch (error) {
        console.warn('Company research failed, using fallback:', error)
      }

      // Prepare enhanced context with research data
      let enhancedContext = industryContext
      let specificInsights = ''

      if (companyResearchData) {
        const insights = companyResearchData.insights || {}
        const contentThemes = insights.content_themes || []
        const recentNews = insights.recent_news || []
        const marketPosition = insights.market_position || []

        specificInsights = [
          ...contentThemes.slice(0, 2).map((theme) => theme.insight),
          ...recentNews.slice(0, 1).map((news) => news.insight),
          ...marketPosition.slice(0, 1).map((pos) => pos.insight),
        ].join('. ')

        enhancedContext = `${industryContext}. Company insights: ${specificInsights}`
      }

      // Calculate character limit (leave 30 characters buffer as requested)
      const maxLength = selectedPlatform.maxLength - 30

      const topic =
        specificInstructions ||
        'AI-powered social media management and automation'

      // STEP 1: Generate caption ONLY (always use 'text' type for caption generation)
      const response = await api.content.generate(
        topic,
        'text', // Always generate text first
        formData.platform,
        specificInstructions,
        companyResearchData
      )

      if (response && response.content) {
        // Get the content from backend (which should already respect character limits)
        let content = response.content.trim()

        // Log if content exceeds limit (this shouldn't happen with improved backend)
        if (content.length > maxLength) {
          console.warn(
            '⚠️ Backend returned content exceeding character limit:',
            content.length,
            '>',
            maxLength
          )
          console.warn('Content preview:', content.substring(0, 100) + '...')
        }

        // Update form with generated content
        const generatedData = {
          content: content,
          title: response.title || `AI Generated ${formData.platform} Post`,
        }

        setFormData((prev) => ({
          ...(prev || {}),
          ...generatedData,
        }))

        showSuccess(
          `✨ Caption created successfully! (${content.length}/${maxLength} chars)`
        )

        // STEP 2: Now generate image based on the caption (if enabled)
        if (generateImageWithContent) {
          showProgress(
            'Now creating a beautiful image to match your caption... 🎨',
            null
          )
          setImageGenerationProgress(true)

          try {
            const imagePrompt = `Create a professional social media image for ${formData.platform} that complements this content: ${content.substring(0, 200)}. Topic: ${topic}. Industry context: ${enhancedContext.substring(0, 300) || 'Professional business context'}`

            const imageData = await api.content.generateImage(
              imagePrompt,
              content,
              formData.platform,
              enhancedContext
            )

            if (
              imageData &&
              imageData.status === 'success' &&
              imageData.image_data_url
            ) {
              const processedImageData = {
                ...imageData,
                image_url: imageData.image_data_url,
                prompt:
                  imageData.prompt?.enhanced ||
                  imageData.prompt?.original ||
                  imagePrompt,
              }
              setGeneratedImage(processedImageData)
              showSuccess(
                '🎉 Complete! Caption and image created successfully!'
              )
            } else if (imageData && imageData.error) {
              showError(
                `Caption created! But I had trouble with the image: Sorry, I'm having trouble generating images right now. Please try again later! 😔 - Lily`
              )
            } else {
              showError(
                `Caption created! But I had trouble generating the image. Please try again later! 😔 - Lily`
              )
            }
          } catch (imageError) {
            logError('Image generation failed:', imageError)
            showError(
              `Caption created! But I had trouble generating the image: Sorry, I'm having trouble generating images right now. Please try again later! 😔 - Lily`
            )
          } finally {
            setImageGenerationProgress(false)
          }
        }
      } else if (response && response.error) {
        showError(
          `Sorry, my AI content generation is currently unavailable. Please try again later! 😔 - Lily`
        )
      } else {
        showError(
          `Sorry, my AI content generation is currently unavailable. Please try again later! 😔 - Lily`
        )
      }
    } catch (error) {
      logError('AI content generation failed:', error)
      showError(
        `Sorry, my AI content generation is currently unavailable. Please try again later! 😔 - Lily`
      )
    } finally {
      setIsGenerating(false)
      setContentGenerationProgress(false)
    }
  }

  const saveToLibrary = async () => {
    if (!formData.content.trim()) {
      showError('Please provide content before saving to library')
      return
    }

    setIsCreating(true)
    try {
      // Determine which image to use based on source
      const imageData =
        imageSource === 'upload' && uploadedImage
          ? {
              image_url: uploadedImage.url,
              image_data: null,
              image_prompt: `Uploaded image: ${uploadedImage.original_filename}`,
              image_source: 'uploaded',
            }
          : {
              image_url:
                generatedImage?.image_url || generatedImage?.image_data_url,
              image_data: generatedImage?.image_base64,
              image_prompt: imagePrompt,
              image_source: 'generated',
            }

      const saveData = {
        ...formData,
        ...imageData,
        industry_context: industryContext,
        research_data: researchData,
        status: 'draft',
        generated_by_ai: true, // Mark as AI generated since it's coming from Create Post
      }

      await api.content.create(saveData)

      showSuccess('Content saved to library successfully!')

      // Option to view in content library
      if (
        window.confirm(
          'Content saved! Would you like to view it in the content library?'
        )
      ) {
        window.location.href = '/content'
      } else {
        // Reset form
        setFormData({
          title: '',
          content: '',
          platform: 'twitter',
          tags: [],
        })
        setGeneratedImage(null)
        setUploadedImage(null)
        setImagePrompt('')
        setImageSource('generate')
      }
    } catch (error) {
      logError('Save to library failed:', error)
      showError('Failed to save content to library')
    } finally {
      setIsCreating(false)
    }
  }

  const getCharacterCount = () => {
    return formData.content.length
  }

  const getCharacterCountColor = () => {
    const count = getCharacterCount()
    const maxLength = selectedPlatform.maxLength - 30 // Account for 30-char buffer
    const percentage = count / maxLength

    if (percentage > 0.95) return 'text-red-600 font-bold'
    if (percentage > 0.85) return 'text-red-500'
    if (percentage > 0.75) return 'text-yellow-600'
    return 'text-gray-600'
  }

  const isOverCharacterLimit = () => {
    return getCharacterCount() > selectedPlatform.maxLength - 30
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    // Validate file type
    const allowedTypes = [
      'image/jpeg',
      'image/jpg',
      'image/png',
      'image/gif',
      'image/webp',
    ]
    if (!allowedTypes.includes(file.type)) {
      showError('Please select a valid image file (JPG, PNG, GIF, WebP)')
      return
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024 // 10MB
    if (file.size > maxSize) {
      showError('File size must be less than 10MB')
      return
    }

    setIsUploading(true)
    try {
      const result = await api.uploadImage(
        file,
        `Image for ${formData.platform} post`
      )
      setUploadedImage(result.file)
      setImageSource('upload')
      showSuccess('Image uploaded successfully!')
    } catch (error) {
      logError('Image upload failed:', error)
      showError(error.message || 'Failed to upload image')
    } finally {
      setIsUploading(false)
    }
  }

  const removeUploadedImage = async () => {
    if (uploadedImage && uploadedImage.filename) {
      try {
        await api.deleteUploadedImage(uploadedImage.filename)
      } catch (error) {
        logError('Failed to delete uploaded image:', error)
      }
    }
    setUploadedImage(null)
    if (imageSource === 'upload') {
      setImageSource('generate')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Create Post
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Create engaging content with AI assistance and industry research
          </p>
          {/* Usage Indicators */}
          {limits && (
            <div className="flex items-center space-x-4 mt-2">
              <div className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
                <DocumentTextIcon className="h-3 w-3" />
                <span>
                  {limits.posts?.daily_limit - (limits.posts?.used_today || 0)}/
                  {limits.posts?.daily_limit} posts today
                </span>
              </div>
              {limits.images?.monthly_limit && (
                <div className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
                  <PhotoIcon className="h-3 w-3" />
                  <span>
                    {limits.images.monthly_limit -
                      (limits.images.used_month || 0)}
                    /{limits.images.monthly_limit} images
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex space-x-3">
          <PlanGate feature="autopilot_research_enabled" fallback={null}>
            <button
              onClick={() => setShowResearchPanel(!showResearchPanel)}
              className="bg-purple-600 text-white px-4 py-2 rounded-md flex items-center space-x-2 hover:bg-purple-700 transition-colors"
            >
              <InformationCircleIcon className="h-4 w-4" />
              <span>Research Insights</span>
            </button>
          </PlanGate>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content Creation */}
        <div className="lg:col-span-2 space-y-6">
          {/* Platform Selection & Specific Instructions */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Post Configuration
            </h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Platform
              </label>
              <select
                value={formData.platform}
                onChange={(e) => handleChange('platform', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {platforms.map((platform) => (
                  <option key={platform.value} value={platform.value}>
                    {platform.label} (max {platform.maxLength - 30} chars + 30
                    buffer)
                  </option>
                ))}
              </select>
            </div>

            {/* Specific Instructions for Lily */}
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Specific Instructions for Lily (Optional)
              </label>
              <textarea
                value={specificInstructions}
                onChange={(e) => setSpecificInstructions(e.target.value)}
                rows={3}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Tell Lily what kind of content you want... (e.g., 'Create a motivational post about productivity tips', 'Share industry insights about AI automation', etc.)"
              />
              <p className="text-xs text-gray-500 mt-1">
                Lily will use your company research data and industry insights
                to create specific, relevant content based on your instructions.
              </p>
            </div>

            {/* Image Generation Opt-out - Plan Gated */}
            <PlanGate
              limit="images"
              limitAction="can_generate"
              fallback={
                <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
                  <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                    <PhotoIcon className="h-4 w-4" />
                    <span>
                      Image generation unavailable - upgrade to enable AI images
                    </span>
                  </div>
                </div>
              }
            >
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!generateImageWithContent}
                      onChange={(e) =>
                        setGenerateImageWithContent(!e.target.checked)
                      }
                      className="mr-2"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Don't generate an AI image with this post
                    </span>
                  </label>
                  {limits?.images && (
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {limits.images.monthly_limit -
                        (limits.images.used_month || 0)}
                      /{limits.images.monthly_limit} remaining
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  By default, Lily will create an AI-generated image to
                  accompany your post. Uncheck this to create text-only content.
                </p>
              </div>
            </PlanGate>
          </div>

          {/* Content Creation */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Content</h3>
              <button
                onClick={generateAIContent}
                disabled={contentGenerationProgress}
                className="bg-blue-600 text-white px-4 py-2 rounded-md flex items-center space-x-2 hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {!contentGenerationProgress ? (
                  <SparklesIcon className="h-4 w-4" />
                ) : null}
                <span>
                  {contentGenerationProgress
                    ? 'Creating Caption & Image...'
                    : 'Generate AI Content'}
                </span>
              </button>
            </div>

            {/* Content Generation Progress */}
            {contentGenerationProgress && (
              <div className="mb-6">
                <ProgressBar
                  isActive={contentGenerationProgress}
                  stages={[
                    '📋 Gathering company research...',
                    '🔍 Analyzing industry insights...',
                    '✍️ Writing your caption...',
                    '✨ Perfecting the message...',
                  ]}
                  duration={6000}
                  onComplete={() => {}}
                />
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title (Optional)
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Post title..."
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-sm font-medium text-gray-700">
                    Content
                  </label>
                  <span className={`text-xs ${getCharacterCountColor()}`}>
                    {getCharacterCount()}/{selectedPlatform.maxLength - 30} (+30
                    buffer)
                  </span>
                </div>
                <textarea
                  value={formData.content}
                  onChange={(e) => handleChange('content', e.target.value)}
                  rows={6}
                  className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    isOverCharacterLimit()
                      ? 'border-red-500 bg-red-50'
                      : 'border-gray-300'
                  }`}
                  placeholder="Write your content here or use AI generation..."
                  maxLength={selectedPlatform.maxLength}
                  required
                />
                {isOverCharacterLimit() && (
                  <p className="text-sm text-red-600 mt-1">
                    ⚠️ Content exceeds recommended limit. Consider shortening to
                    stay within the 30-character safety buffer.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Image Selection and Display */}
          {generateImageWithContent && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Post Image
                </h3>
                <div className="text-sm text-blue-600">
                  {imageGenerationProgress ? (
                    <span className="flex items-center">
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-600"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Creating image...
                    </span>
                  ) : isUploading ? (
                    <span className="flex items-center">
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-600"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Uploading image...
                    </span>
                  ) : (
                    <span>🎨 Choose how to add an image</span>
                  )}
                </div>
              </div>

              {/* Image Source Selection Tabs */}
              <div className="mb-6">
                <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
                  <button
                    onClick={() => setImageSource('generate')}
                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      imageSource === 'generate'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <SparklesIcon className="h-4 w-4 inline mr-2" />
                    Generate with AI
                  </button>
                  <button
                    onClick={() => setImageSource('upload')}
                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      imageSource === 'upload'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <PhotoIcon className="h-4 w-4 inline mr-2" />
                    Upload Your Image
                  </button>
                </div>
              </div>

              {/* Upload Image Section */}
              {imageSource === 'upload' && (
                <div className="mb-6">
                  {!uploadedImage ? (
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
                      <div className="text-center">
                        <PhotoIcon className="mx-auto h-12 w-12 text-gray-400" />
                        <div className="mt-4">
                          <label
                            htmlFor="image-upload"
                            className="cursor-pointer"
                          >
                            <span className="mt-2 block text-sm font-medium text-gray-900">
                              Upload an image
                            </span>
                            <span className="mt-1 block text-sm text-gray-600">
                              PNG, JPG, GIF, WebP up to 10MB
                            </span>
                          </label>
                          <input
                            id="image-upload"
                            type="file"
                            accept="image/*"
                            onChange={handleFileUpload}
                            className="sr-only"
                            disabled={isUploading}
                          />
                        </div>
                        <div className="mt-4">
                          <button
                            onClick={() =>
                              document.getElementById('image-upload').click()
                            }
                            disabled={isUploading}
                            className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                          >
                            Choose File
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          Uploaded Image
                        </span>
                        <button
                          onClick={removeUploadedImage}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="mt-3">
                        <img
                          src={uploadedImage.url}
                          alt={
                            uploadedImage.original_filename || 'Uploaded image'
                          }
                          className="max-w-full h-auto rounded-lg shadow-md max-h-64 mx-auto"
                        />
                      </div>
                      <div className="mt-2 text-xs text-gray-500">
                        {uploadedImage.original_filename} (
                        {(uploadedImage.size / (1024 * 1024)).toFixed(1)}MB)
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* AI Generation Section */}
              {imageSource === 'generate' && (
                <div>
                  {/* Image Generation Progress */}
                  {imageGenerationProgress && (
                    <div className="mb-6">
                      <ProgressBar
                        isActive={imageGenerationProgress}
                        stages={[
                          'Processing your caption...',
                          'Creating visual concept...',
                          'Generating image...',
                          'Adding finishing touches...',
                        ]}
                        duration={8000}
                        onComplete={() => {}}
                      />
                    </div>
                  )}

                  {generatedImage ? (
                    <div className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          AI Generated Image
                        </span>
                        <div className="flex items-center space-x-2">
                          {generatedImage.status === 'success' ? (
                            <CheckCircleIcon className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircleIcon className="h-4 w-4 text-red-500" />
                          )}
                          <span className="text-xs text-gray-600">
                            {generatedImage.model || 'AI Generated'}
                          </span>
                        </div>
                      </div>

                      {generatedImage.image_url && (
                        <div className="mt-4">
                          <div
                            className="cursor-pointer group relative overflow-hidden rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-200"
                            onClick={() =>
                              window.open(generatedImage.image_url, '_blank')
                            }
                          >
                            <img
                              src={generatedImage.image_url}
                              alt="Generated content"
                              className="w-full h-auto object-contain bg-gray-50"
                              style={{
                                maxWidth: 'none',
                                minHeight: '200px',
                                maxHeight: '500px',
                              }}
                            />
                            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-opacity duration-200 flex items-center justify-center">
                              <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                <svg
                                  className="h-8 w-8 text-white"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"
                                  />
                                </svg>
                              </div>
                            </div>
                          </div>
                          <p className="text-xs text-gray-500 mt-2 text-center">
                            Click image to view full size in new tab
                          </p>
                        </div>
                      )}

                      {generatedImage.error && (
                        <p className="text-sm text-red-600 mt-2">
                          {generatedImage.error}
                        </p>
                      )}

                      <p className="text-xs text-gray-500 mt-2">
                        Prompt: {generatedImage.prompt}
                      </p>
                    </div>
                  ) : (
                    !imageGenerationProgress && (
                      <div className="text-center py-8 text-gray-500">
                        <PhotoIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                        <p className="text-sm">
                          Your image will appear here after generating content
                        </p>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-600">
                Ready to save your content to the library?
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={() => {
                    setFormData({
                      title: '',
                      content: '',
                      platform: 'twitter',
                      tags: [],
                    })
                    setGeneratedImage(null)
                    setImagePrompt('')
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Clear
                </button>
                <button
                  onClick={saveToLibrary}
                  disabled={isCreating || !formData.content.trim()}
                  className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {isCreating ? (
                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  ) : (
                    <DocumentTextIcon className="h-4 w-4" />
                  )}
                  <span>{isCreating ? 'Saving...' : 'Save to Library'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Real-time Preview and Research */}
        <div className="lg:col-span-1 space-y-6">
          {/* Real-time Content Preview */}
          <RealtimeContentPreview
            content={formData.content || ''}
            platform={formData.platform}
            image={
              imageSource === 'upload' && uploadedImage
                ? uploadedImage.url
                : generatedImage?.image_url || generatedImage?.image_data_url
            }
            title={formData.title}
          />

          {/* Research Panel */}
          <div
            className={`bg-white rounded-lg shadow p-6 transition-all duration-300 ${showResearchPanel ? 'block' : 'hidden lg:block'}`}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Industry Research
              </h3>
              <button
                onClick={conductIndustryResearch}
                disabled={isResearching}
                className="text-blue-600 hover:text-blue-700 text-sm"
              >
                {isResearching ? 'Researching...' : 'Refresh'}
              </button>
            </div>

            {isResearching ? (
              <div className="text-center py-8">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
                <p className="text-sm text-gray-600">
                  Conducting industry research...
                </p>
              </div>
            ) : researchData ? (
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">
                    Current Trends
                  </h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {(researchData?.trends || []).map((trend, index) => (
                      <li key={index} className="flex items-start">
                        <span className="mr-2">•</span>
                        <span>{trend}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 mb-2">
                    Content Suggestions
                  </h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {(researchData?.contentSuggestions || []).map(
                      (suggestion, index) => (
                        <li key={index} className="flex items-start">
                          <span className="mr-2">💡</span>
                          <span>{suggestion}</span>
                        </li>
                      )
                    )}
                  </ul>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Key Topics</h4>
                  <div className="flex flex-wrap gap-2">
                    {(researchData?.keyTopics || []).map((topic, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full cursor-pointer hover:bg-blue-200"
                        onClick={() =>
                          setImagePrompt(
                            (prev) => prev + (prev ? ', ' : '') + topic
                          )
                        }
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 mb-2">
                    Market Insights
                  </h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {(researchData?.competitorInsights || []).map(
                      (insight, index) => (
                        <li key={index} className="flex items-start">
                          <span className="mr-2">📊</span>
                          <span>{insight}</span>
                        </li>
                      )
                    )}
                  </ul>
                </div>

                <div className="border-t pt-4">
                  <p className="text-xs text-gray-500">
                    <strong>Industry Context:</strong> {industryContext}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-600">
                No research data available
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
