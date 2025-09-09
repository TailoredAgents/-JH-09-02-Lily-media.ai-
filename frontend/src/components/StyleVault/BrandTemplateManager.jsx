import React, { useState, useEffect } from 'react'
import {
  DocumentTextIcon,
  PlusIcon,
  TrashIcon,
  DuplicateIcon,
  PencilIcon,
  EyeIcon,
  ShareIcon,
  DownloadIcon,
  StarIcon,
  TagIcon,
  ClockIcon,
  CheckCircleIcon,
  XMarkIcon,
  SwatchIcon,
  PhotoIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid'

const TEMPLATE_CATEGORIES = [
  {
    id: 'content',
    name: 'Content Templates',
    icon: DocumentTextIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    description: 'Pre-written content templates for consistent messaging',
  },
  {
    id: 'visual',
    name: 'Visual Templates',
    icon: PhotoIcon,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    description: 'Image and design templates with brand elements',
  },
  {
    id: 'color_schemes',
    name: 'Color Schemes',
    icon: SwatchIcon,
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
    description: 'Predefined color combinations for various use cases',
  },
  {
    id: 'campaigns',
    name: 'Campaign Templates',
    icon: SparklesIcon,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    description: 'Complete campaign templates with all assets',
  },
]

const TEMPLATE_TYPES = {
  content: [
    'Social Media Post',
    'Blog Introduction',
    'Product Description',
    'Email Newsletter',
    'Press Release',
    'Ad Copy',
    'Caption Template',
    'Announcement',
  ],
  visual: [
    'Instagram Story',
    'Instagram Post',
    'Facebook Post',
    'LinkedIn Post',
    'Twitter Header',
    'Blog Banner',
    'Ad Creative',
    'Logo Placement',
  ],
  color_schemes: [
    'Primary Brand',
    'Seasonal',
    'Product Launch',
    'Event Special',
    'Holiday Theme',
    'Professional',
    'Creative',
    'Minimal',
  ],
  campaigns: [
    'Product Launch',
    'Brand Awareness',
    'Seasonal Sale',
    'Community Event',
    'User Generated Content',
    'Educational Series',
    'Behind the Scenes',
    'Customer Testimonials',
  ],
}

function TemplateCard({ template, onEdit, onDelete, onDuplicate, onPreview, onToggleFavorite }) {
  const category = TEMPLATE_CATEGORIES.find(c => c.id === template.category)
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start space-x-3 flex-1">
            <div className={`p-2 rounded-lg ${category?.bgColor}`}>
              <category.icon className={`h-5 w-5 ${category?.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-900 truncate">
                {template.name}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {template.type} • {category?.name}
              </p>
              {template.description && (
                <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                  {template.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-1 ml-2">
            <button
              onClick={() => onToggleFavorite(template.id)}
              className="p-1 text-gray-400 hover:text-yellow-500 rounded"
              aria-label={template.isFavorite ? 'Remove from favorites' : 'Add to favorites'}
              type="button"
            >
              {template.isFavorite ? (
                <StarIconSolid className="h-4 w-4 text-yellow-500" />
              ) : (
                <StarIcon className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {/* Tags */}
        {template.tags && template.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {template.tags.slice(0, 3).map(tag => (
              <span
                key={tag}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
              >
                {tag}
              </span>
            ))}
            {template.tags.length > 3 && (
              <span className="text-xs text-gray-500">
                +{template.tags.length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Preview Content */}
        <div className="mb-4">
          {template.category === 'content' && template.content && (
            <div className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-600 mb-1">Content Preview:</p>
              <p className="text-sm text-gray-800 line-clamp-3">
                {template.content}
              </p>
            </div>
          )}

          {template.category === 'color_schemes' && template.colors && (
            <div className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-600 mb-2">Color Palette:</p>
              <div className="flex space-x-2">
                {template.colors.slice(0, 6).map((color, index) => (
                  <div
                    key={index}
                    className="w-6 h-6 rounded border border-gray-300"
                    style={{ backgroundColor: color }}
                    title={color}
                  />
                ))}
                {template.colors.length > 6 && (
                  <span className="text-xs text-gray-500 self-center">
                    +{template.colors.length - 6}
                  </span>
                )}
              </div>
            </div>
          )}

          {template.category === 'visual' && template.imageUrl && (
            <div className="bg-gray-50 rounded p-2">
              <img
                src={template.imageUrl}
                alt={`${template.name} preview`}
                className="w-full h-24 object-cover rounded"
              />
            </div>
          )}
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
          <div className="flex items-center space-x-3">
            <span className="flex items-center">
              <ClockIcon className="h-3 w-3 mr-1" />
              {new Date(template.updatedAt).toLocaleDateString()}
            </span>
            {template.usageCount && (
              <span>Used {template.usageCount} times</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex space-x-2">
            <button
              onClick={() => onPreview(template)}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              type="button"
            >
              Preview
            </button>
            <button
              onClick={() => onEdit(template)}
              className="text-xs text-purple-600 hover:text-purple-700 font-medium"
              type="button"
            >
              Edit
            </button>
            <button
              onClick={() => onDuplicate(template)}
              className="text-xs text-green-600 hover:text-green-700 font-medium"
              type="button"
            >
              Duplicate
            </button>
          </div>

          <button
            onClick={() => onDelete(template.id)}
            className="p-1 text-gray-400 hover:text-red-500 rounded"
            aria-label="Delete template"
            type="button"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function TemplateEditor({ template, category, onSave, onCancel, isEditing = false }) {
  const [formData, setFormData] = useState({
    name: template?.name || '',
    description: template?.description || '',
    type: template?.type || TEMPLATE_TYPES[category]?.[0] || '',
    tags: template?.tags || [],
    content: template?.content || '',
    colors: template?.colors || ['#3B82F6'],
    imageUrl: template?.imageUrl || '',
    variables: template?.variables || [],
  })

  const [newTag, setNewTag] = useState('')
  const [newVariable, setNewVariable] = useState({ name: '', placeholder: '', required: false })

  const handleSave = () => {
    const templateData = {
      id: template?.id || Date.now().toString(),
      category,
      ...formData,
      updatedAt: new Date().toISOString(),
      createdAt: template?.createdAt || new Date().toISOString(),
      isFavorite: template?.isFavorite || false,
      usageCount: template?.usageCount || 0,
    }
    
    onSave(templateData)
  }

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }))
      setNewTag('')
    }
  }

  const removeTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }))
  }

  const addColor = () => {
    setFormData(prev => ({
      ...prev,
      colors: [...prev.colors, '#000000']
    }))
  }

  const updateColor = (index, color) => {
    setFormData(prev => ({
      ...prev,
      colors: prev.colors.map((c, i) => i === index ? color : c)
    }))
  }

  const removeColor = (index) => {
    if (formData.colors.length > 1) {
      setFormData(prev => ({
        ...prev,
        colors: prev.colors.filter((_, i) => i !== index)
      }))
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {isEditing ? 'Edit Template' : 'Create New Template'}
        </h3>
      </div>

      <div className="space-y-6">
        {/* Basic Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Template Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Enter template name"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type *
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              required
            >
              {TEMPLATE_TYPES[category]?.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            rows={3}
            placeholder="Describe this template and when to use it"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tags
          </label>
          <div className="flex flex-wrap gap-2 mb-3">
            {formData.tags.map(tag => (
              <span
                key={tag}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-800"
              >
                {tag}
                <button
                  onClick={() => removeTag(tag)}
                  className="ml-2 text-purple-600 hover:text-purple-800"
                  type="button"
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex space-x-2">
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addTag()}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Add a tag"
            />
            <button
              onClick={addTag}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
              type="button"
            >
              Add
            </button>
          </div>
        </div>

        {/* Category-specific fields */}
        {category === 'content' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Content Template *
            </label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              rows={6}
              placeholder="Enter your content template. Use {{variable_name}} for dynamic content."
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Use double curly braces like {{company_name}} for variables that can be replaced
            </p>
          </div>
        )}

        {category === 'color_schemes' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Colors *
            </label>
            <div className="space-y-3">
              {formData.colors.map((color, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <input
                    type="color"
                    value={color}
                    onChange={(e) => updateColor(index, e.target.value)}
                    className="w-12 h-10 border border-gray-300 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={color}
                    onChange={(e) => updateColor(index, e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="#000000"
                  />
                  {formData.colors.length > 1 && (
                    <button
                      onClick={() => removeColor(index)}
                      className="p-2 text-red-500 hover:text-red-700"
                      type="button"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addColor}
                className="inline-flex items-center text-sm text-purple-600 hover:text-purple-700 font-medium"
                type="button"
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                Add Color
              </button>
            </div>
          </div>
        )}

        {category === 'visual' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Image URL
            </label>
            <input
              type="url"
              value={formData.imageUrl}
              onChange={(e) => setFormData(prev => ({ ...prev, imageUrl: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              placeholder="https://example.com/image.jpg"
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
            type="button"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!formData.name.trim()}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
            type="button"
          >
            {isEditing ? 'Update Template' : 'Create Template'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function BrandTemplateManager({ 
  templates = [], 
  onSave, 
  onDelete, 
  onDuplicate 
}) {
  const [selectedCategory, setSelectedCategory] = useState('content')
  const [isCreating, setIsCreating] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterFavorites, setFilterFavorites] = useState(false)

  const filteredTemplates = templates.filter(template => {
    const matchesCategory = template.category === selectedCategory
    const matchesSearch = searchQuery === '' || 
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesFavorites = !filterFavorites || template.isFavorite

    return matchesCategory && matchesSearch && matchesFavorites
  })

  const handleSave = (templateData) => {
    onSave(templateData)
    setIsCreating(false)
    setEditingTemplate(null)
  }

  const handleEdit = (template) => {
    setEditingTemplate(template)
  }

  const handleDelete = (templateId) => {
    if (window.confirm('Are you sure you want to delete this template?')) {
      onDelete(templateId)
    }
  }

  const handleDuplicate = (template) => {
    const duplicatedTemplate = {
      ...template,
      id: Date.now().toString(),
      name: `${template.name} (Copy)`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      usageCount: 0,
    }
    onSave(duplicatedTemplate)
  }

  const handleToggleFavorite = (templateId) => {
    const template = templates.find(t => t.id === templateId)
    if (template) {
      onSave({
        ...template,
        isFavorite: !template.isFavorite,
        updatedAt: new Date().toISOString(),
      })
    }
  }

  const selectedCategoryInfo = TEMPLATE_CATEGORIES.find(c => c.id === selectedCategory)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Brand Templates</h2>
          <p className="text-sm text-gray-600 mt-1">
            Create and manage reusable brand templates for consistent content
          </p>
        </div>

        {!isCreating && !editingTemplate && (
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
            type="button"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            New Template
          </button>
        )}
      </div>

      {!isCreating && !editingTemplate && (
        <>
          {/* Category Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8">
              {TEMPLATE_CATEGORIES.map(category => {
                const Icon = category.icon
                const count = templates.filter(t => t.category === category.id).length
                
                return (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                      selectedCategory === category.id
                        ? 'border-purple-500 text-purple-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                    type="button"
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {category.name}
                    {count > 0 && (
                      <span className="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs">
                        {count}
                      </span>
                    )}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Search and Filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder={`Search ${selectedCategoryInfo?.name.toLowerCase()}...`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
              </div>
            </div>

            <button
              onClick={() => setFilterFavorites(!filterFavorites)}
              className={`inline-flex items-center px-4 py-2 border rounded-md text-sm font-medium transition-colors ${
                filterFavorites
                  ? 'border-yellow-300 bg-yellow-50 text-yellow-700'
                  : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
              }`}
              type="button"
            >
              <StarIcon className="h-4 w-4 mr-2" />
              Favorites Only
            </button>
          </div>

          {/* Templates Grid */}
          {filteredTemplates.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTemplates.map(template => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onDuplicate={handleDuplicate}
                  onToggleFavorite={handleToggleFavorite}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <selectedCategoryInfo.icon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No {selectedCategoryInfo?.name.toLowerCase()} found
              </h3>
              <p className="text-gray-600 mb-6">
                {searchQuery || filterFavorites 
                  ? 'Try adjusting your filters or search terms'
                  : selectedCategoryInfo?.description
                }
              </p>
              {!searchQuery && !filterFavorites && (
                <button
                  onClick={() => setIsCreating(true)}
                  className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                  type="button"
                >
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Create Your First Template
                </button>
              )}
            </div>
          )}
        </>
      )}

      {/* Template Editor */}
      {(isCreating || editingTemplate) && (
        <TemplateEditor
          template={editingTemplate}
          category={selectedCategory}
          onSave={handleSave}
          onCancel={() => {
            setIsCreating(false)
            setEditingTemplate(null)
          }}
          isEditing={!!editingTemplate}
        />
      )}
    </div>
  )
}