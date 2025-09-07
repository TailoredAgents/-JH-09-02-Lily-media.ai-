import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEnhancedApi } from '../hooks/useEnhancedApi'
import { useNotifications } from '../hooks/useNotifications'
import FocusTrappedModal from './FocusTrappedModal'
import {
  ArrowPathIcon,
  PhotoIcon,
  SparklesIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'

export default function RegenerateImageModal({
  content,
  isOpen,
  onClose,
  onSuccess,
}) {
  const [customPrompt, setCustomPrompt] = useState('')
  const [keepOriginalContext, setKeepOriginalContext] = useState(true)
  const [qualityPreset, setQualityPreset] = useState('standard')

  const api = useEnhancedApi()
  const { addNotification } = useNotifications()
  const queryClient = useQueryClient()

  const qualityOptions = [
    {
      value: 'draft',
      label: 'Draft (Fast)',
      description: 'Quick generation for testing',
    },
    {
      value: 'standard',
      label: 'Standard',
      description: 'Good quality, balanced speed',
    },
    {
      value: 'premium',
      label: 'Premium (Slow)',
      description: 'Highest quality, slower generation',
    },
    {
      value: 'story',
      label: 'Story Format',
      description: 'Optimized for vertical stories',
    },
    {
      value: 'banner',
      label: 'Banner Format',
      description: 'Optimized for wide banners',
    },
  ]

  const regenerateImage = useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/content/regenerate-image', data)
      return response.data
    },
    onSuccess: (result) => {
      addNotification({
        type: 'success',
        title: 'Image Regenerated Successfully!',
        message: `New image created with your custom prompt. ${result.user_settings_applied ? 'Your brand settings were applied.' : ''}`,
      })

      // Invalidate content queries to refresh the list
      queryClient.invalidateQueries({ queryKey: ['content'] })

      if (onSuccess) {
        onSuccess(result)
      }

      handleClose()
    },
    onError: (error) => {
      addNotification({
        type: 'error',
        title: 'Image Regeneration Failed',
        message:
          error.response?.data?.detail ||
          'Failed to regenerate image. Please try again.',
      })
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()

    if (!customPrompt.trim()) {
      addNotification({
        type: 'error',
        title: 'Custom Prompt Required',
        message: 'Please enter a description for your new image.',
      })
      return
    }

    regenerateImage.mutate({
      content_id: content.id,
      custom_prompt: customPrompt.trim(),
      platform: content.platform || 'instagram',
      quality_preset: qualityPreset,
      keep_original_context: keepOriginalContext,
    })
  }

  const handleClose = () => {
    if (!regenerateImage.isPending) {
      setCustomPrompt('')
      setKeepOriginalContext(true)
      setQualityPreset('standard')
      onClose()
    }
  }

  const suggestedPrompts = [
    'A modern, professional image with clean lines and bright colors',
    'Vibrant and energetic visual with dynamic composition',
    'Minimalist design with focus on typography and whitespace',
    'Tech-focused image with futuristic elements and gradients',
    'Warm and welcoming image with natural lighting',
  ]

  if (!isOpen || !content) return null

  return (
    <FocusTrappedModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Regenerate Image"
      size="lg"
    >
      <form onSubmit={handleSubmit}>
        <div className="px-4 pt-5 pb-4 sm:p-6">
          {/* Header Info */}
          <div className="flex items-center space-x-3 mb-6">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <ArrowPathIcon className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500">
                Create a new image for "{content.title}"
              </p>
            </div>
          </div>

          {/* Original Content Preview */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Original Content
            </h4>
            <p className="text-sm text-gray-700 line-clamp-3">
              {content.content}
            </p>
            <div className="mt-2 flex items-center space-x-2 text-xs text-gray-500">
              <PhotoIcon className="w-4 h-4" />
              <span className="capitalize">
                {content.platform || 'All platforms'}
              </span>
            </div>
          </div>

          {/* Custom Prompt */}
          <div className="mb-6">
            <label
              htmlFor="customPrompt"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Custom Image Description *
            </label>
            <textarea
              id="customPrompt"
              rows={4}
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Describe the image you want to generate..."
              disabled={regenerateImage.isPending}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Be specific about style, colors, composition, and mood
            </p>
          </div>

          {/* Suggested Prompts */}
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Suggested Prompts
            </h4>
            <div className="space-y-2">
              {suggestedPrompts.map((prompt, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => setCustomPrompt(prompt)}
                  disabled={regenerateImage.isPending}
                  className="w-full text-left p-3 text-sm text-gray-600 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
                >
                  <SparklesIcon className="w-4 h-4 inline mr-2 text-gray-400" />
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Options */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Quality Preset */}
            <div>
              <label
                htmlFor="qualityPreset"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Quality Preset
              </label>
              <select
                id="qualityPreset"
                value={qualityPreset}
                onChange={(e) => setQualityPreset(e.target.value)}
                disabled={regenerateImage.isPending}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:bg-gray-50"
              >
                {qualityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                {
                  qualityOptions.find((opt) => opt.value === qualityPreset)
                    ?.description
                }
              </p>
            </div>

            {/* Keep Original Context */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Context Options
              </label>
              <div className="flex items-center">
                <input
                  id="keepContext"
                  type="checkbox"
                  checked={keepOriginalContext}
                  onChange={(e) => setKeepOriginalContext(e.target.checked)}
                  disabled={regenerateImage.isPending}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                />
                <label
                  htmlFor="keepContext"
                  className="ml-2 text-sm text-gray-700"
                >
                  Keep original post context
                </label>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Include the original post text to inform image generation
              </p>
            </div>
          </div>

          {/* Info Banner */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex">
              <ExclamationCircleIcon className="h-5 w-5 text-blue-400 mt-0.5 mr-3" />
              <div className="text-sm">
                <p className="text-blue-800 font-medium mb-1">
                  Your brand settings will be automatically applied
                </p>
                <p className="text-blue-700">
                  The image will be generated using your configured industry
                  presets, colors, and visual style preferences for consistent
                  branding.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="submit"
            disabled={regenerateImage.isPending || !customPrompt.trim()}
            className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {regenerateImage.isPending ? (
              <>
                <ArrowPathIcon className="animate-spin -ml-1 mr-2 h-4 w-4" />
                Generating...
              </>
            ) : (
              <>
                <ArrowPathIcon className="-ml-1 mr-2 h-4 w-4" />
                Regenerate Image
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleClose}
            disabled={regenerateImage.isPending}
            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        </div>
      </form>
    </FocusTrappedModal>
  )
}
