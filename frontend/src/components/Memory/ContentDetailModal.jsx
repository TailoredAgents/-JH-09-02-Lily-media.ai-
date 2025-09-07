import { useState } from 'react'
import {
  HeartIcon,
  ShareIcon,
  EyeIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import FocusTrappedModal from '../FocusTrappedModal'

export default function ContentDetailModal({
  content,
  isOpen,
  onClose,
  onRepurpose,
  onEdit,
  onDelete,
}) {
  const [showRepurposeOptions, setShowRepurposeOptions] = useState(false)

  if (!isOpen || !content) return null

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const repurposeOptions = [
    {
      id: 'twitter-thread',
      title: 'Twitter Thread',
      description: 'Break into 5-7 connected tweets',
      platform: 'Twitter',
      effort: 'Low',
    },
    {
      id: 'linkedin-carousel',
      title: 'LinkedIn Carousel',
      description: 'Create visual slides with key points',
      platform: 'LinkedIn',
      effort: 'Medium',
    },
    {
      id: 'instagram-story',
      title: 'Instagram Stories',
      description: 'Design multiple story frames',
      platform: 'Instagram',
      effort: 'Medium',
    },
    {
      id: 'blog-post',
      title: 'Blog Post',
      description: 'Expand into detailed article',
      platform: 'Blog',
      effort: 'High',
    },
    {
      id: 'video-script',
      title: 'Video Script',
      description: 'Convert to video format',
      platform: 'YouTube',
      effort: 'High',
    },
  ]

  const getEffortColor = (effort) => {
    switch (effort) {
      case 'Low':
        return 'text-green-600 bg-green-100'
      case 'Medium':
        return 'text-yellow-600 bg-yellow-100'
      case 'High':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <FocusTrappedModal
      isOpen={isOpen}
      onClose={onClose}
      title="Content Details"
      size="xl"
    >
      <div className="bg-white px-4 pt-5 pb-4 sm:p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {content.title}
            </h3>
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full capitalize">
                {content.type.replace('_', ' ')}
              </span>
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded-full capitalize">
                {content.platform}
              </span>
              <span>{formatDate(content.created_at)}</span>
              {content.similarity_score && (
                <span className="text-green-600 font-medium">
                  {Math.round(content.similarity_score * 100)}% similarity match
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => onEdit && onEdit(content)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
            >
              <PencilIcon className="h-5 w-5" />
            </button>
            <button
              onClick={() => onDelete && onDelete(content.id)}
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
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Content Body */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-3">Content</h4>
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {content.content}
                </p>
              </div>
            </div>

            {/* Tags */}
            {content.tags && content.tags.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Tags</h4>
                <div className="flex flex-wrap gap-2">
                  {content.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-50 text-blue-600 text-sm rounded-full"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Repurpose Options */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium text-gray-900">Repurpose Ideas</h4>
                <button
                  onClick={() => setShowRepurposeOptions(!showRepurposeOptions)}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {showRepurposeOptions ? 'Hide' : 'Show All'} Options
                </button>
              </div>

              {showRepurposeOptions && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {repurposeOptions.map((option) => (
                    <div
                      key={option.id}
                      className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() =>
                        onRepurpose && onRepurpose(content, option)
                      }
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h5 className="font-medium text-gray-900">
                          {option.title}
                        </h5>
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${getEffortColor(option.effort)}`}
                        >
                          {option.effort}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        {option.description}
                      </p>
                      <span className="text-xs text-gray-500">
                        {option.platform}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Engagement Stats */}
            <div className="bg-white border rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-4">Performance</h4>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <EyeIcon className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Views</span>
                  </div>
                  <span className="font-medium">
                    {content.engagement?.views?.toLocaleString() || 0}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <HeartIcon className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Likes</span>
                  </div>
                  <span className="font-medium">
                    {content.engagement?.likes?.toLocaleString() || 0}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <ShareIcon className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Shares</span>
                  </div>
                  <span className="font-medium">
                    {content.engagement?.shares?.toLocaleString() || 0}
                  </span>
                </div>

                <div className="pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">
                      Total Engagement
                    </span>
                    <span className="font-bold text-blue-600">
                      {(
                        (content.engagement?.likes || 0) +
                        (content.engagement?.shares || 0)
                      ).toLocaleString()}
                    </span>
                  </div>

                  {content.engagement?.views && (
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-sm text-gray-600">
                        Engagement Rate
                      </span>
                      <span className="text-sm font-medium text-green-600">
                        {(
                          ((content.engagement.likes +
                            content.engagement.shares) /
                            content.engagement.views) *
                          100
                        ).toFixed(1)}
                        %
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white border rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-4">Quick Actions</h4>

              <div className="space-y-2">
                <button
                  onClick={() => onRepurpose && onRepurpose(content)}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 transition-colors"
                >
                  <ArrowPathIcon className="h-4 w-4" />
                  <span>Repurpose Content</span>
                </button>

                <button className="w-full flex items-center space-x-2 px-3 py-2 text-sm bg-green-50 text-green-600 rounded-md hover:bg-green-100 transition-colors">
                  <DocumentDuplicateIcon className="h-4 w-4" />
                  <span>Duplicate</span>
                </button>

                <button className="w-full flex items-center space-x-2 px-3 py-2 text-sm bg-purple-50 text-purple-600 rounded-md hover:bg-purple-100 transition-colors">
                  <ShareIcon className="h-4 w-4" />
                  <span>Find Similar</span>
                </button>
              </div>
            </div>

            {/* Similar Content */}
            {content.similarity_score && (
              <div className="bg-white border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-4">
                  Similar Content
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Based on {Math.round(content.similarity_score * 100)}%
                  similarity score
                </p>

                <div className="space-y-2">
                  <div className="text-xs text-gray-500 p-2 bg-gray-50 rounded">
                    Similar content suggestions will appear here when the FAISS
                    backend is connected.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </FocusTrappedModal>
  )
}
