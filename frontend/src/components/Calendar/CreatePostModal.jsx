import { useState } from 'react'
import { CalendarIcon, ClockIcon } from '@heroicons/react/24/outline'
import FocusTrappedModal from '../FocusTrappedModal'

const platforms = {
  LinkedIn: {
    color: 'bg-blue-600',
    textColor: 'text-blue-600',
    lightBg: 'bg-blue-50',
  },
  Twitter: {
    color: 'bg-sky-500',
    textColor: 'text-sky-500',
    lightBg: 'bg-sky-50',
  },
  Instagram: {
    color: 'bg-pink-600',
    textColor: 'text-pink-600',
    lightBg: 'bg-pink-50',
  },
  Facebook: {
    color: 'bg-indigo-600',
    textColor: 'text-indigo-600',
    lightBg: 'bg-indigo-50',
  },
}

export default function CreatePostModal({
  isOpen,
  onClose,
  selectedDate,
  onCreatePost,
}) {
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    platform: 'LinkedIn',
    date: selectedDate || new Date().toISOString().split('T')[0],
    time: '09:00',
    status: 'scheduled',
  })

  const [errors, setErrors] = useState({})

  const handleSubmit = (e) => {
    e.preventDefault()

    // Validation
    const newErrors = {}
    if (!formData.title.trim()) newErrors.title = 'Title is required'
    if (!formData.content.trim()) newErrors.content = 'Content is required'
    if (!formData.date) newErrors.date = 'Date is required'
    if (!formData.time) newErrors.time = 'Time is required'

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    // Create new post object
    const newPost = {
      id: Date.now(),
      ...formData,
      createdAt: new Date().toISOString(),
    }

    onCreatePost(newPost)
    onClose()

    // Reset form
    setFormData({
      title: '',
      content: '',
      platform: 'LinkedIn',
      date: selectedDate || new Date().toISOString().split('T')[0],
      time: '09:00',
      status: 'scheduled',
    })
    setErrors({})
  }

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }))
    }
  }

  return (
    <FocusTrappedModal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Post"
      size="md"
    >
      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="p-6 space-y-4"
        data-testid="create-post-form"
      >
        {/* Title */}
        <div>
          <label
            htmlFor="post-title"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Title
          </label>
          <input
            id="post-title"
            type="text"
            value={formData.title}
            onChange={(e) => handleInputChange('title', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.title ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Enter post title..."
          />
          {errors.title && (
            <p className="text-red-500 text-xs mt-1">{errors.title}</p>
          )}
        </div>

        {/* Content */}
        <div>
          <label
            htmlFor="post-content"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Content
          </label>
          <textarea
            id="post-content"
            value={formData.content}
            onChange={(e) => handleInputChange('content', e.target.value)}
            rows={4}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none ${
              errors.content ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Write your post content..."
          />
          {errors.content && (
            <p className="text-red-500 text-xs mt-1">{errors.content}</p>
          )}
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{formData.content.length} characters</span>
            <span>Max: 280 for Twitter, 3000 for LinkedIn</span>
          </div>
        </div>

        {/* Platform */}
        <div>
          <label
            htmlFor="post-platform"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Platform
          </label>
          <select
            id="post-platform"
            value={formData.platform}
            onChange={(e) => handleInputChange('platform', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {Object.keys(platforms).map((platform) => (
              <option key={platform} value={platform}>
                {platform}
              </option>
            ))}
          </select>
        </div>

        {/* Date and Time */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="post-date"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              <CalendarIcon className="h-4 w-4 inline mr-1" />
              Date
            </label>
            <input
              id="post-date"
              type="date"
              value={formData.date}
              onChange={(e) => handleInputChange('date', e.target.value)}
              min={new Date().toISOString().split('T')[0]}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.date ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            {errors.date && (
              <p className="text-red-500 text-xs mt-1">{errors.date}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="post-time"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              <ClockIcon className="h-4 w-4 inline mr-1" />
              Time
            </label>
            <input
              id="post-time"
              type="time"
              value={formData.time}
              onChange={(e) => handleInputChange('time', e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.time ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            {errors.time && (
              <p className="text-red-500 text-xs mt-1">{errors.time}</p>
            )}
          </div>
        </div>

        {/* Status */}
        <div>
          <label
            htmlFor="post-status"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Status
          </label>
          <select
            id="post-status"
            value={formData.status}
            onChange={(e) => handleInputChange('status', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="draft">Draft</option>
            <option value="scheduled">Scheduled</option>
          </select>
        </div>

        {/* Platform Preview */}
        <div
          className={`p-3 rounded-lg ${platforms[formData.platform]?.lightBg || 'bg-gray-50'}`}
        >
          <div className="flex items-start space-x-2">
            <div
              className={`w-2 h-2 rounded-full mt-2 ${platforms[formData.platform]?.color}`}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">
                {formData.title || 'Post Title'}
              </p>
              <p className="text-xs text-gray-600 mt-1">
                {formData.content || 'Post content will appear here...'}
              </p>
              <div className="flex items-center space-x-2 mt-2">
                <span className="text-xs text-gray-500">
                  {formData.platform}
                </span>
                <span className="text-xs text-gray-500">•</span>
                <span className="text-xs text-gray-500">
                  {formData.date} at {formData.time}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
          >
            Create Post
          </button>
        </div>
      </form>
    </FocusTrappedModal>
  )
}
