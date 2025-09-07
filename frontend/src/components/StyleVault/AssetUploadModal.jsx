import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  CloudArrowUpIcon,
  XMarkIcon,
  PhotoIcon,
  DocumentTextIcon,
  TagIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'

const AssetUploadModal = ({ onClose, onUpload, uploadProgress }) => {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [assetType, setAssetType] = useState('images')
  const [uploadTags, setUploadTags] = useState('')
  const [dragActive, setDragActive] = useState(false)

  const onDrop = useCallback((acceptedFiles) => {
    const filesWithPreview = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
    }))
    setSelectedFiles(prev => [...prev, ...filesWithPreview])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: getAcceptedFileTypes(),
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    multiple: true,
  })

  function getAcceptedFileTypes() {
    switch (assetType) {
      case 'logos':
        return {
          'image/*': ['.png', '.jpg', '.jpeg', '.svg', '.webp']
        }
      case 'images':
        return {
          'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.gif']
        }
      case 'fonts':
        return {
          'font/*': ['.woff', '.woff2', '.ttf', '.otf'],
          'application/*': ['.woff', '.woff2']
        }
      default:
        return {
          'image/*': ['.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif']
        }
    }
  }

  const removeFile = (fileId) => {
    setSelectedFiles(prev => {
      const updated = prev.filter(f => f.id !== fileId)
      // Revoke object URLs to prevent memory leaks
      const removedFile = prev.find(f => f.id === fileId)
      if (removedFile?.preview) {
        URL.revokeObjectURL(removedFile.preview)
      }
      return updated
    })
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    const files = selectedFiles.map(f => f.file)
    await onUpload(files, assetType, {
      tags: uploadTags.split(',').map(tag => tag.trim()).filter(Boolean)
    })

    // Clean up object URLs
    selectedFiles.forEach(file => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview)
      }
    })
    
    setSelectedFiles([])
    onClose()
  }

  const isUploading = uploadProgress[assetType] !== undefined

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
      <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Upload Brand Assets</h3>
            <p className="text-sm text-gray-500 mt-1">
              Add images, logos, and fonts to your brand vault
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isUploading}
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Asset Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Asset Type
            </label>
            <div className="flex space-x-4">
              <button
                onClick={() => setAssetType('logos')}
                className={`flex items-center px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  assetType === 'logos'
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <PhotoIcon className="w-4 h-4 mr-2" />
                Logos
              </button>
              <button
                onClick={() => setAssetType('images')}
                className={`flex items-center px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  assetType === 'images'
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <PhotoIcon className="w-4 h-4 mr-2" />
                Images
              </button>
              <button
                onClick={() => setAssetType('fonts')}
                className={`flex items-center px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  assetType === 'fonts'
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <DocumentTextIcon className="w-4 h-4 mr-2" />
                Fonts
              </button>
            </div>
          </div>

          {/* File Drop Zone */}
          <div>
            <div 
              {...getRootProps()} 
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
                isDragActive || dragActive
                  ? 'border-purple-500 bg-purple-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <CloudArrowUpIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              {isDragActive ? (
                <div>
                  <p className="text-lg text-purple-600 font-medium">Drop files here</p>
                  <p className="text-sm text-gray-500 mt-1">Release to upload</p>
                </div>
              ) : (
                <div>
                  <p className="text-lg text-gray-600 font-medium">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    {getFileTypeDescription()}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Selected Files */}
          {selectedFiles.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">
                Selected Files ({selectedFiles.length})
              </h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {selectedFiles.map((fileData) => (
                  <div key={fileData.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      {fileData.preview ? (
                        <img 
                          src={fileData.preview} 
                          alt={fileData.name}
                          className="w-10 h-10 rounded object-cover"
                        />
                      ) : (
                        <div className="w-10 h-10 bg-gray-200 rounded flex items-center justify-center">
                          <DocumentTextIcon className="w-5 h-5 text-gray-500" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {fileData.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatFileSize(fileData.size)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => removeFile(fileData.id)}
                      className="text-gray-400 hover:text-red-600"
                      disabled={isUploading}
                    >
                      <XMarkIcon className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tags Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags (optional)
            </label>
            <div className="relative">
              <TagIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={uploadTags}
                onChange={(e) => setUploadTags(e.target.value)}
                placeholder="Enter tags separated by commas (e.g., logo, brand, primary)"
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                disabled={isUploading}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Tags help organize and search your assets
            </p>
          </div>

          {/* Upload Progress */}
          {isUploading && (
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-blue-900">
                  Uploading {assetType}...
                </span>
                <span className="text-sm text-blue-600">
                  {Math.round(uploadProgress[assetType] || 0)}%
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress[assetType] || 0}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            disabled={isUploading}
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || isUploading}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? 'Uploading...' : `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  )

  function getFileTypeDescription() {
    switch (assetType) {
      case 'logos':
        return 'PNG, JPG, SVG, WebP up to 10MB each'
      case 'images':
        return 'PNG, JPG, WebP, GIF up to 10MB each'
      case 'fonts':
        return 'WOFF, WOFF2, TTF, OTF up to 5MB each'
      default:
        return 'Multiple file types supported'
    }
  }
}

export default AssetUploadModal