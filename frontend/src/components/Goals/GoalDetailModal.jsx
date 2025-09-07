import { useState } from 'react'
import {
  PencilIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { ProgressTimelineChart } from '../Charts/ProgressChart'
import FocusTrappedModal from '../FocusTrappedModal'

export default function GoalDetailModal({
  goal,
  isOpen,
  onClose,
  onUpdate,
  onDelete,
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    current_value: goal?.current_value || 0,
    target_value: goal?.target_value || 0,
    target_date: goal?.target_date || '',
    status: goal?.status || 'active',
  })

  if (!isOpen || !goal) return null

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const getDaysRemaining = () => {
    const targetDate = new Date(goal.target_date)
    const today = new Date()
    const diffTime = targetDate - today
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'active':
        return 'bg-blue-100 text-blue-800'
      case 'paused':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleSaveEdit = () => {
    const updatedGoal = {
      ...goal,
      ...editForm,
      current_value: parseFloat(editForm.current_value),
      target_value: parseFloat(editForm.target_value),
      progress_percentage:
        (parseFloat(editForm.current_value) /
          parseFloat(editForm.target_value)) *
        100,
    }

    onUpdate(updatedGoal)
    setIsEditing(false)
  }

  const handleStatusChange = (newStatus) => {
    const updatedGoal = {
      ...goal,
      status: newStatus,
    }
    onUpdate(updatedGoal)
  }

  return (
    <FocusTrappedModal
      isOpen={isOpen}
      onClose={onClose}
      title={goal.title}
      size="xl"
    >
      <div className="px-4 pt-5 pb-4 sm:p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <h3 className="text-xl font-semibold text-gray-900">
                {goal.title}
              </h3>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(goal.status)}`}
              >
                {goal.status}
              </span>
            </div>
            <p className="text-gray-600">{goal.description}</p>
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
              <span>Platform: {goal.platform}</span>
              <span>Type: {goal.goal_type.replace('_', ' ')}</span>
              <span>Created: {formatDate(goal.start_date)}</span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {goal.status === 'active' && (
              <>
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
                >
                  <PencilIcon className="h-5 w-5" />
                </button>
                <button
                  onClick={() => handleStatusChange('paused')}
                  className="p-2 text-yellow-400 hover:text-yellow-600 rounded-md hover:bg-yellow-50"
                >
                  <PauseIcon className="h-5 w-5" />
                </button>
              </>
            )}

            {goal.status === 'paused' && (
              <button
                onClick={() => handleStatusChange('active')}
                className="p-2 text-green-400 hover:text-green-600 rounded-md hover:bg-green-50"
              >
                <PlayIcon className="h-5 w-5" />
              </button>
            )}

            <button
              onClick={() => onDelete(goal.id)}
              className="p-2 text-red-400 hover:text-red-600 rounded-md hover:bg-red-50"
            >
              <TrashIcon className="h-5 w-5" />
            </button>

            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Progress Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Progress Overview */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-4">
                Progress Overview
              </h4>

              {isEditing ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Current Value
                      </label>
                      <input
                        type="number"
                        value={editForm.current_value}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            current_value: e.target.value,
                          }))
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Target Value
                      </label>
                      <input
                        type="number"
                        value={editForm.target_value}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            target_value: e.target.value,
                          }))
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Target Date
                    </label>
                    <input
                      type="date"
                      value={editForm.target_date}
                      onChange={(e) =>
                        setEditForm((prev) => ({
                          ...prev,
                          target_date: e.target.value,
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex space-x-2">
                    <button
                      onClick={handleSaveEdit}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                      Save Changes
                    </button>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-2xl font-bold text-gray-900">
                      {goal.current_value.toLocaleString()} /{' '}
                      {goal.target_value.toLocaleString()}
                    </span>
                    <span
                      className={`text-lg font-semibold ${goal.is_on_track ? 'text-green-600' : 'text-yellow-600'}`}
                    >
                      {Math.round(goal.progress_percentage)}%
                    </span>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                    <div
                      className={`h-3 rounded-full transition-all duration-300 ${
                        goal.status === 'completed'
                          ? 'bg-green-500'
                          : goal.is_on_track
                            ? 'bg-blue-500'
                            : 'bg-yellow-500'
                      }`}
                      style={{
                        width: `${Math.min(goal.progress_percentage, 100)}%`,
                      }}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Target Date</span>
                      <div className="font-medium">
                        {formatDate(goal.target_date)}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-500">Days Remaining</span>
                      <div className="font-medium">
                        {getDaysRemaining() > 0
                          ? `${getDaysRemaining()} days`
                          : 'Overdue'}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-500">Status</span>
                      <div
                        className={`font-medium ${goal.is_on_track ? 'text-green-600' : 'text-yellow-600'}`}
                      >
                        {goal.is_on_track ? 'On Track' : 'Behind Schedule'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Progress Timeline Chart */}
            <div className="bg-white border rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-4">
                Progress Timeline
              </h4>
              <ProgressTimelineChart goal={goal} />
            </div>
          </div>

          {/* Right Column - Milestones & Actions */}
          <div className="space-y-6">
            {/* Milestones */}
            <div className="bg-white border rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-4">Milestones</h4>

              {goal.milestones.length > 0 ? (
                <div className="space-y-3">
                  {goal.milestones.map((milestone) => (
                    <div
                      key={milestone.id}
                      className="flex items-start space-x-3"
                    >
                      <div className="flex-shrink-0 w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                        <div className="w-2 h-2 bg-green-600 rounded-full"></div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          {milestone.description}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatDate(milestone.achieved_at)}
                        </p>
                      </div>
                      <div className="text-xs font-medium text-gray-500">
                        {milestone.percentage}%
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">
                  No milestones achieved yet.
                </p>
              )}
            </div>

            {/* Quick Stats */}
            <div className="bg-white border rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-4">Quick Stats</h4>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Daily Target</span>
                  <span className="text-sm font-medium">
                    {Math.round(
                      (goal.target_value - goal.current_value) /
                        Math.max(getDaysRemaining(), 1)
                    )}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Completion Rate</span>
                  <span className="text-sm font-medium">
                    {goal.progress_percentage.toFixed(1)}%
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Time Elapsed</span>
                  <span className="text-sm font-medium">
                    {Math.round(
                      ((new Date() - new Date(goal.start_date)) /
                        (new Date(goal.target_date) -
                          new Date(goal.start_date))) *
                        100
                    )}
                    %
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            {goal.status === 'active' && (
              <div className="bg-white border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-4">Actions</h4>

                <div className="space-y-2">
                  <button className="w-full text-left px-3 py-2 text-sm bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 transition-colors">
                    Update Progress
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm bg-green-50 text-green-600 rounded-md hover:bg-green-100 transition-colors">
                    Add Milestone
                  </button>
                  <button className="w-full text-left px-3 py-2 text-sm bg-purple-50 text-purple-600 rounded-md hover:bg-purple-100 transition-colors">
                    View Analytics
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </FocusTrappedModal>
  )
}
