import { useState } from 'react'
import {
  CalendarIcon,
  ChartBarIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline'
import FocusTrappedModal from '../FocusTrappedModal'

const goalTypes = [
  {
    value: 'follower_growth',
    label: 'Follower Growth',
    icon: ChartBarIcon,
    description: 'Increase your follower count on social platforms',
    unit: 'followers',
  },
  {
    value: 'engagement_rate',
    label: 'Engagement Rate',
    icon: TrophyIcon,
    description: 'Improve interaction rates on your content',
    unit: '%',
  },
  {
    value: 'content_volume',
    label: 'Content Volume',
    icon: CalendarIcon,
    description: 'Increase the number of posts published',
    unit: 'posts',
  },
  {
    value: 'reach_increase',
    label: 'Reach Increase',
    icon: ChartBarIcon,
    description: 'Expand your content reach and impressions',
    unit: 'views',
  },
]

const platforms = [
  { value: 'all', label: 'All Platforms' },
  { value: 'twitter', label: 'Twitter' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
]

export default function CreateGoalModal({ isOpen, onClose, onSubmit }) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    goal_type: 'follower_growth',
    target_value: '',
    current_value: '',
    target_date: '',
    platform: 'all',
    milestones: [],
  })

  const [errors, setErrors] = useState({})

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: '',
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required'
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required'
    }

    if (!formData.target_value || formData.target_value <= 0) {
      newErrors.target_value = 'Target value must be greater than 0'
    }

    if (!formData.current_value || formData.current_value < 0) {
      newErrors.current_value = 'Current value must be 0 or greater'
    }

    if (
      parseFloat(formData.current_value) >= parseFloat(formData.target_value)
    ) {
      newErrors.current_value = 'Current value must be less than target value'
    }

    if (!formData.target_date) {
      newErrors.target_date = 'Target date is required'
    } else {
      const targetDate = new Date(formData.target_date)
      const today = new Date()
      today.setHours(0, 0, 0, 0)

      if (targetDate <= today) {
        newErrors.target_date = 'Target date must be in the future'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    const goalData = {
      ...formData,
      target_value: parseFloat(formData.target_value),
      current_value: parseFloat(formData.current_value),
      start_date: new Date().toISOString().split('T')[0],
      status: 'active',
      progress_percentage:
        (parseFloat(formData.current_value) /
          parseFloat(formData.target_value)) *
        100,
      is_on_track: true,
    }

    onSubmit(goalData)

    // Reset form
    setFormData({
      title: '',
      description: '',
      goal_type: 'follower_growth',
      target_value: '',
      current_value: '',
      target_date: '',
      platform: 'all',
      milestones: [],
    })
    setErrors({})
  }

  const selectedGoalType = goalTypes.find(
    (type) => type.value === formData.goal_type
  )

  return (
    <FocusTrappedModal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Goal"
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <div className="px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div className="w-full">
            <div className="space-y-4">
              {/* Goal Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Goal Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {goalTypes.map((type) => (
                    <label
                      key={type.value}
                      className={`relative flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                        formData.goal_type === type.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200'
                      }`}
                    >
                      <input
                        type="radio"
                        name="goal_type"
                        value={type.value}
                        checked={formData.goal_type === type.value}
                        onChange={handleInputChange}
                        className="sr-only"
                      />
                      <type.icon className="h-5 w-5 text-gray-400 mr-2" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {type.label}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
                {selectedGoalType && (
                  <p className="mt-2 text-xs text-gray-500">
                    {selectedGoalType.description}
                  </p>
                )}
              </div>

              {/* Title */}
              <div>
                <label
                  htmlFor="title"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Goal Title
                </label>
                <input
                  id="title"
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.title ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="e.g., Grow LinkedIn Following"
                />
                {errors.title && (
                  <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                )}
              </div>

              {/* Description */}
              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Description
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={3}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.description ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Describe what you want to achieve..."
                />
                {errors.description && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.description}
                  </p>
                )}
              </div>

              {/* Platform */}
              <div>
                <label
                  htmlFor="platform"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Platform
                </label>
                <select
                  id="platform"
                  name="platform"
                  value={formData.platform}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {platforms.map((platform) => (
                    <option key={platform.value} value={platform.value}>
                      {platform.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Values */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="current_value"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Current Value
                  </label>
                  <div className="relative">
                    <input
                      id="current_value"
                      type="number"
                      name="current_value"
                      value={formData.current_value}
                      onChange={handleInputChange}
                      className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        errors.current_value
                          ? 'border-red-300'
                          : 'border-gray-300'
                      }`}
                      placeholder="0"
                      min="0"
                    />
                    {selectedGoalType && (
                      <span className="absolute right-3 top-2 text-sm text-gray-500">
                        {selectedGoalType.unit}
                      </span>
                    )}
                  </div>
                  {errors.current_value && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.current_value}
                    </p>
                  )}
                </div>

                <div>
                  <label
                    htmlFor="target_value"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Target Value
                  </label>
                  <div className="relative">
                    <input
                      id="target_value"
                      type="number"
                      name="target_value"
                      value={formData.target_value}
                      onChange={handleInputChange}
                      className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        errors.target_value
                          ? 'border-red-300'
                          : 'border-gray-300'
                      }`}
                      placeholder="1000"
                      min="1"
                    />
                    {selectedGoalType && (
                      <span className="absolute right-3 top-2 text-sm text-gray-500">
                        {selectedGoalType.unit}
                      </span>
                    )}
                  </div>
                  {errors.target_value && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.target_value}
                    </p>
                  )}
                </div>
              </div>

              {/* Target Date */}
              <div>
                <label
                  htmlFor="target_date"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Target Date
                </label>
                <input
                  id="target_date"
                  type="date"
                  name="target_date"
                  value={formData.target_date}
                  onChange={handleInputChange}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.target_date ? 'border-red-300' : 'border-gray-300'
                  }`}
                  min={new Date().toISOString().split('T')[0]}
                />
                {errors.target_date && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.target_date}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="submit"
            className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Create Goal
          </button>
          <button
            type="button"
            onClick={onClose}
            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancel
          </button>
        </div>
      </form>
    </FocusTrappedModal>
  )
}
