import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  CloudArrowUpIcon,
  XMarkIcon,
  DocumentTextIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

const FontUploadModal = ({ onClose, onUpload }) => {
  const [selectedFile, setSelectedFile] = useState(null)
  const [fontData, setFontData] = useState({
    name: '',
    family: '',
    style: 'normal',
    weight: 400,
    display: 'swap',
    description: ''
  })
  const [isUploading, setIsUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      setSelectedFile(file)
      
      // Auto-populate font name from filename
      const baseName = file.name.replace(/\.[^/.]+$/, '') // Remove extension
      if (!fontData.name) {
        setFontData(prev => ({
          ...prev,
          name: baseName,
          family: baseName.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        }))
      }
    }
  }, [fontData.name])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'font/*': ['.woff', '.woff2', '.ttf', '.otf'],
      'application/*': ['.woff', '.woff2']
    },
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    multiple: false,
  })

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const handleUpload = async () => {
    if (!selectedFile || !fontData.name.trim() || !fontData.family.trim()) return

    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('font_file', selectedFile)
      formData.append('name', fontData.name.trim())
      formData.append('family', fontData.family.trim())
      formData.append('style', fontData.style)
      formData.append('weight', fontData.weight.toString())
      formData.append('display', fontData.display)
      
      if (fontData.description.trim()) {
        formData.append('description', fontData.description.trim())
      }

      await onUpload(formData)
      onClose()
    } catch (error) {
      console.error('Font upload failed:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const removeFile = () => {
    setSelectedFile(null)
    setFontData(prev => ({ ...prev, name: '', family: '' }))
  }

  const weightOptions = [
    { value: 100, label: '100 - Thin' },
    { value: 200, label: '200 - Extra Light' },
    { value: 300, label: '300 - Light' },
    { value: 400, label: '400 - Regular' },
    { value: 500, label: '500 - Medium' },
    { value: 600, label: '600 - Semi Bold' },
    { value: 700, label: '700 - Bold' },
    { value: 800, label: '800 - Extra Bold' },
    { value: 900, label: '900 - Black' },
  ]

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
      <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Upload Font</h3>
            <p className="text-sm text-gray-500 mt-1">
              Add a custom font to your brand typography collection
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
          {/* Font File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Font File
            </label>
            
            {!selectedFile ? (
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
                    <p className="text-lg text-purple-600 font-medium">Drop font file here</p>
                    <p className="text-sm text-gray-500 mt-1">Release to upload</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-lg text-gray-600 font-medium">
                      Click to upload or drag and drop
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      WOFF, WOFF2, TTF, OTF up to 5MB
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <DocumentTextIcon className="w-8 h-8 text-purple-600" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(selectedFile.size)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={removeFile}
                    className="text-gray-400 hover:text-red-600"
                    disabled={isUploading}
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Font Metadata */}
          {selectedFile && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Font Name *
                  </label>
                  <input
                    type="text"
                    value={fontData.name}
                    onChange={(e) => setFontData(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="e.g., Montserrat Bold"
                    disabled={isUploading}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Font Family *
                  </label>
                  <input
                    type="text"
                    value={fontData.family}
                    onChange={(e) => setFontData(prev => ({ ...prev, family: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="e.g., Montserrat"
                    disabled={isUploading}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Font Style
                  </label>
                  <select
                    value={fontData.style}
                    onChange={(e) => setFontData(prev => ({ ...prev, style: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    disabled={isUploading}
                  >
                    <option value="normal">Normal</option>
                    <option value="italic">Italic</option>
                    <option value="oblique">Oblique</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Font Weight
                  </label>
                  <select
                    value={fontData.weight}
                    onChange={(e) => setFontData(prev => ({ ...prev, weight: parseInt(e.target.value) }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    disabled={isUploading}
                  >
                    {weightOptions.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Font Display
                  </label>
                  <select
                    value={fontData.display}
                    onChange={(e) => setFontData(prev => ({ ...prev, display: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    disabled={isUploading}
                  >
                    <option value="swap">Swap</option>
                    <option value="block">Block</option>
                    <option value="fallback">Fallback</option>
                    <option value="optional">Optional</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={fontData.description}
                  onChange={(e) => setFontData(prev => ({ ...prev, description: e.target.value }))}
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Describe this font and its intended use..."
                  disabled={isUploading}
                />
              </div>

              {/* Font Preview */}
              {fontData.family && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Font Preview
                  </label>
                  <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div 
                      className="space-y-2"
                      style={{
                        fontFamily: `"${fontData.family}", sans-serif`,
                        fontWeight: fontData.weight,
                        fontStyle: fontData.style
                      }}
                    >
                      <p className="text-2xl text-gray-900">
                        The quick brown fox
                      </p>
                      <p className="text-lg text-gray-700">
                        ABCDEFGHIJKLMNOPQRSTUVWXYZ
                      </p>
                      <p className="text-sm text-gray-600">
                        abcdefghijklmnopqrstuvwxyz 1234567890
                      </p>
                    </div>
                    <p className="text-xs text-gray-500 mt-3">
                      Preview uses fallback fonts until the font is uploaded and processed
                    </p>
                  </div>
                </div>
              )}

              {/* Usage Info */}
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex">
                  <InformationCircleIcon className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="ml-3">
                    <p className="text-sm text-blue-800 font-medium">Font Usage</p>
                    <p className="text-sm text-blue-700 mt-1">
                      Once uploaded, this font will be available for use in your content templates and can be referenced in your visual guidelines. 
                      For best performance, use WOFF2 format when possible.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {isUploading && (
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-3"></div>
                <span className="text-sm font-medium text-blue-900">
                  Uploading and processing font...
                </span>
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
            disabled={!selectedFile || !fontData.name.trim() || !fontData.family.trim() || isUploading}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? 'Uploading...' : 'Upload Font'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default FontUploadModal