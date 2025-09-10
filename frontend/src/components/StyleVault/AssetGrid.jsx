import { useState } from 'react'
import FocusTrappedModal from '../FocusTrappedModal'
import {
  PhotoIcon,
  EyeIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  StarIcon,
  ClockIcon,
  TagIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { StarIcon as StarSolidIcon } from '@heroicons/react/24/solid'

const AssetGrid = ({
  assets,
  type,
  viewMode,
  searchTerm,
  onDelete,
  onSelect,
  selectedAssets,
}) => {
  const [showPreview, setShowPreview] = useState(null)

  // Filter assets based on search term
  const filteredAssets = assets.filter(
    (asset) =>
      !searchTerm ||
      asset.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      asset.tags?.some((tag) =>
        tag.toLowerCase().includes(searchTerm.toLowerCase())
      )
  )

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const toggleFavorite = async (assetId) => {
    // Implementation would depend on backend API
    console.log('Toggle favorite for asset:', assetId)
  }

  if (filteredAssets.length === 0) {
    return (
      <div className="text-center py-12">
        <PhotoIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No assets found
        </h3>
        <p className="text-gray-500">
          {searchTerm
            ? `No ${type} assets match your search criteria.`
            : `No ${type} assets uploaded yet.`}
        </p>
      </div>
    )
  }

  if (viewMode === 'list') {
    return (
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {filteredAssets.map((asset) => (
            <li key={asset.id}>
              <div className="px-4 py-4 flex items-center justify-between hover:bg-gray-50">
                <div className="flex items-center min-w-0 flex-1">
                  <input
                    type="checkbox"
                    checked={selectedAssets.includes(asset.id)}
                    onChange={() => onSelect(asset.id)}
                    className="h-4 w-4 text-purple-600 rounded border-gray-300 mr-4"
                  />
                  <div className="flex-shrink-0 w-16 h-12 bg-gray-100 rounded overflow-hidden">
                    {asset.thumbnail_url ? (
                      <img
                        src={asset.thumbnail_url}
                        alt={asset.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <PhotoIcon className="w-6 h-6 text-gray-400" />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1 ml-4">
                    <div className="flex items-center">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {asset.name}
                      </p>
                      {asset.is_favorite && (
                        <StarSolidIcon className="w-4 h-4 text-yellow-400 ml-2" />
                      )}
                    </div>
                    <div className="flex items-center mt-1 text-sm text-gray-500 space-x-4">
                      <span>{formatFileSize(asset.file_size)}</span>
                      <span>
                        {asset.width}x{asset.height}
                      </span>
                      <span className="flex items-center">
                        <ClockIcon className="w-4 h-4 mr-1" />
                        {formatDate(asset.created_at)}
                      </span>
                    </div>
                    {asset.tags && asset.tags.length > 0 && (
                      <div className="flex items-center mt-2 space-x-1">
                        <TagIcon className="w-3 h-3 text-gray-400" />
                        {asset.tags.slice(0, 3).map((tag, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                          >
                            {tag}
                          </span>
                        ))}
                        {asset.tags.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{asset.tags.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => toggleFavorite(asset.id)}
                    className="p-2 text-gray-400 hover:text-yellow-500 rounded"
                    title="Toggle favorite"
                  >
                    {asset.is_favorite ? (
                      <StarSolidIcon className="w-4 h-4 text-yellow-400" />
                    ) : (
                      <StarIcon className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => setShowPreview(asset)}
                    className="p-2 text-gray-400 hover:text-blue-600 rounded"
                    title="Preview"
                  >
                    <EyeIcon className="w-4 h-4" />
                  </button>
                  <a
                    href={asset.download_url}
                    download={asset.name}
                    className="p-2 text-gray-400 hover:text-green-600 rounded"
                    title="Download"
                  >
                    <ArrowDownTrayIcon className="w-4 h-4" />
                  </a>
                  <button
                    onClick={() => onDelete(asset.id)}
                    className="p-2 text-gray-400 hover:text-red-600 rounded"
                    title="Delete"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  // Grid view
  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {filteredAssets.map((asset) => (
          <div
            key={asset.id}
            className="group relative bg-white rounded-lg border border-gray-200 hover:border-purple-300 hover:shadow-md transition-all duration-200"
          >
            <div className="relative">
              {/* Selection checkbox */}
              <div className="absolute top-2 left-2 z-10">
                <input
                  type="checkbox"
                  checked={selectedAssets.includes(asset.id)}
                  onChange={() => onSelect(asset.id)}
                  className="h-4 w-4 text-purple-600 rounded border-gray-300 shadow-sm"
                />
              </div>

              {/* Favorite star */}
              {asset.is_favorite && (
                <div className="absolute top-2 right-2 z-10" aria-label="Favorite asset">
                  <StarSolidIcon className="w-4 h-4 text-yellow-400" aria-hidden="true" />
                </div>
              )}

              {/* Asset preview */}
              <div className="aspect-w-4 aspect-h-3 rounded-t-lg overflow-hidden bg-gray-100">
                {asset.thumbnail_url ? (
                  <img
                    src={asset.thumbnail_url}
                    alt={`${type === 'logos' ? 'Logo' : type === 'images' ? 'Image' : 'Asset'}: ${asset.name}`}
                    className="w-full h-32 object-cover group-hover:scale-105 transition-transform duration-200"
                  />
                ) : (
                  <div className="w-full h-32 flex items-center justify-center" aria-label="No preview available">
                    <PhotoIcon className="w-8 h-8 text-gray-400" aria-hidden="true" />
                  </div>
                )}

                {/* Overlay actions */}
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all duration-200 flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setShowPreview(asset)}
                      className="p-2 bg-white rounded-full text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                      aria-label={`Preview ${asset.name}`}
                    >
                      <EyeIcon className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <a
                      href={asset.download_url}
                      download={asset.name}
                      className="p-2 bg-white rounded-full text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                      aria-label={`Download ${asset.name}`}
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" aria-hidden="true" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Asset info */}
              <div className="p-3">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium text-gray-900 truncate flex-1">
                    {asset.name}
                  </p>
                  <button
                    onClick={() => onDelete(asset.id)}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 ml-2 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 rounded focus:opacity-100"
                    aria-label={`Delete ${asset.name}`}
                  >
                    <TrashIcon className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>

                <div className="text-xs text-gray-500 space-y-1">
                  <div className="flex justify-between">
                    <span>{formatFileSize(asset.file_size)}</span>
                    <span>
                      {asset.width}x{asset.height}
                    </span>
                  </div>
                  <div className="truncate">{formatDate(asset.created_at)}</div>
                </div>

                {/* Tags */}
                {asset.tags && asset.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {asset.tags.slice(0, 2).map((tag, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800"
                      >
                        {tag}
                      </span>
                    ))}
                    {asset.tags.length > 2 && (
                      <span className="text-xs text-gray-400">
                        +{asset.tags.length - 2}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <AssetPreviewModal
          asset={showPreview}
          onClose={() => setShowPreview(null)}
        />
      )}
    </>
  )
}

// Asset Preview Modal Component
const AssetPreviewModal = ({ asset, onClose }) => {
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <FocusTrappedModal
      isOpen={true}
      onClose={onClose}
      title={asset.name}
      size="xl"
    >
      <div className="p-6">
        <p className="text-sm text-gray-500 mb-6">
          {formatFileSize(asset.file_size)} • {asset.width}x{asset.height} • 
          Uploaded {formatDate(asset.created_at)}
        </p>

          <div
            className="flex items-center justify-center bg-gray-50 rounded-lg mb-6"
            style={{ minHeight: '400px' }}
          >
            <img
              src={asset.url || asset.thumbnail_url}
              alt={asset.name}
              className="max-w-full max-h-96 object-contain rounded"
            />
          </div>

          {/* Asset metadata */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">
                Asset Details
              </h4>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">File Size:</dt>
                  <dd className="text-sm text-gray-900">
                    {formatFileSize(asset.file_size)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Dimensions:</dt>
                  <dd className="text-sm text-gray-900">
                    {asset.width}x{asset.height}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Format:</dt>
                  <dd className="text-sm text-gray-900">
                    {asset.format?.toUpperCase() || 'N/A'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Uploaded:</dt>
                  <dd className="text-sm text-gray-900">
                    {formatDate(asset.created_at)}
                  </dd>
                </div>
              </dl>
            </div>

            {asset.tags && asset.tags.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Tags</h4>
                <div className="flex flex-wrap gap-2">
                  {asset.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

        <div className="mt-6 flex justify-end space-x-3">
          <a
            href={asset.download_url}
            download={asset.name}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <ArrowDownTrayIcon className="w-4 h-4 mr-2" />
            Download
          </a>
          <button
            onClick={onClose}
            className="inline-flex items-center px-4 py-2 bg-purple-600 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-purple-700"
          >
            Close
          </button>
        </div>
      </div>
    </FocusTrappedModal>
  )
}

export default AssetGrid
