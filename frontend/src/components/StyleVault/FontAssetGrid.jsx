import { useState } from 'react'
import {
  DocumentTextIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

const FontAssetGrid = ({ fonts, searchTerm, onDelete, onUpdate }) => {
  const [editingFont, setEditingFont] = useState(null)
  const [editName, setEditName] = useState('')

  // Filter fonts based on search term
  const filteredFonts = fonts.filter(font => 
    !searchTerm || 
    font.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    font.family?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    font.style?.toLowerCase().includes(searchTerm.toLowerCase())
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
      day: 'numeric'
    })
  }

  const getFontWeight = (weight) => {
    const weights = {
      100: 'Thin',
      200: 'Extra Light',
      300: 'Light',
      400: 'Regular',
      500: 'Medium',
      600: 'Semi Bold',
      700: 'Bold',
      800: 'Extra Bold',
      900: 'Black'
    }
    return weights[weight] || weight
  }

  const startEdit = (font) => {
    setEditingFont(font.id)
    setEditName(font.name)
  }

  const saveEdit = async () => {
    if (editName.trim() && editName !== fonts.find(f => f.id === editingFont)?.name) {
      await onUpdate(editingFont, { name: editName.trim() })
    }
    cancelEdit()
  }

  const cancelEdit = () => {
    setEditingFont(null)
    setEditName('')
  }

  if (filteredFonts.length === 0) {
    return (
      <div className="text-center py-12">
        <DocumentTextIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No fonts found</h3>
        <p className="text-gray-500">
          {searchTerm 
            ? `No fonts match your search criteria.`
            : `No fonts uploaded yet.`
          }
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {filteredFonts.map((font) => (
        <div key={font.id} className="bg-white border border-gray-200 rounded-lg p-6 hover:border-purple-300 transition-colors">
          <div className="flex items-center justify-between">
            {/* Font Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-3 mb-3">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <DocumentTextIcon className="w-6 h-6 text-purple-600" />
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  {editingFont === font.id ? (
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="flex-1 text-lg font-semibold text-gray-900 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-purple-500"
                        onKeyPress={(e) => e.key === 'Enter' && saveEdit()}
                        autoFocus
                      />
                      <button
                        onClick={saveEdit}
                        className="text-green-600 hover:text-green-700"
                      >
                        <CheckIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="text-red-600 hover:text-red-700"
                      >
                        <XMarkIcon className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {font.name}
                      </h3>
                      <button
                        onClick={() => startEdit(font)}
                        className="text-gray-400 hover:text-gray-600"
                        title="Edit name"
                      >
                        <PencilIcon className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    <span>{font.family}</span>
                    {font.style && <span>{font.style}</span>}
                    {font.weight && <span>{getFontWeight(font.weight)}</span>}
                    <span>{formatFileSize(font.file_size)}</span>
                    <span>Uploaded {formatDate(font.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Font Preview */}
              <div className="ml-15">
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div 
                    className="space-y-2"
                    style={{ 
                      fontFamily: font.family,
                      fontWeight: font.weight || 400,
                      fontStyle: font.style || 'normal'
                    }}
                  >
                    <p className="text-2xl text-gray-900">
                      The quick brown fox jumps
                    </p>
                    <p className="text-lg text-gray-700">
                      ABCDEFGHIJKLMNOPQRSTUVWXYZ
                    </p>
                    <p className="text-sm text-gray-600">
                      abcdefghijklmnopqrstuvwxyz 1234567890
                    </p>
                  </div>
                </div>

                {/* Font Technical Details */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <dt className="text-gray-500">Format</dt>
                    <dd className="font-medium text-gray-900">{font.format?.toUpperCase() || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Version</dt>
                    <dd className="font-medium text-gray-900">{font.version || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Glyphs</dt>
                    <dd className="font-medium text-gray-900">{font.glyph_count || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Languages</dt>
                    <dd className="font-medium text-gray-900">
                      {font.supported_languages ? font.supported_languages.slice(0, 3).join(', ') : 'N/A'}
                      {font.supported_languages && font.supported_languages.length > 3 && (
                        <span className="text-gray-500"> +{font.supported_languages.length - 3}</span>
                      )}
                    </dd>
                  </div>
                </div>

                {/* Font Usage Examples */}
                {font.css_declarations && (
                  <div className="mt-4">
                    <details className="group">
                      <summary className="text-sm text-purple-600 hover:text-purple-700 cursor-pointer">
                        View CSS Usage
                      </summary>
                      <div className="mt-2 p-3 bg-gray-900 rounded text-sm">
                        <code className="text-green-400">
                          {font.css_declarations.map((declaration, index) => (
                            <div key={index} className="whitespace-pre">
                              {declaration}
                            </div>
                          ))}
                        </code>
                      </div>
                    </details>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-2 ml-4">
              <a
                href={font.download_url}
                download={font.original_filename}
                className="p-2 text-gray-400 hover:text-blue-600 rounded"
                title="Download font"
              >
                <ArrowDownTrayIcon className="w-5 h-5" />
              </a>
              <button
                onClick={() => onDelete(font.id)}
                className="p-2 text-gray-400 hover:text-red-600 rounded"
                title="Delete font"
              >
                <TrashIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default FontAssetGrid