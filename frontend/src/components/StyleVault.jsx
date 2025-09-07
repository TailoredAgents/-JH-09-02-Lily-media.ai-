import React, { useState, useEffect } from 'react'
import { usePlan } from '../contexts/PlanContext'
import { usePlanConditionals } from '../hooks/usePlanConditionals'
import PlanGate from './PlanGate'
import EnhancedPlanGate, { FeatureGate, TierGate } from './enhanced/EnhancedPlanGate'
import { useNotifications } from '../hooks/useNotifications'
import api from '../services/api'
import {
  SwatchIcon,
  PhotoIcon,
  DocumentTextIcon,
  PlusIcon,
  TrashIcon,
  ArrowUpTrayIcon,
  EyeIcon,
  CheckCircleIcon,
  XMarkIcon,
  PaintBrushIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  CloudArrowUpIcon,
  ArrowDownTrayIcon,
  TagIcon,
  DocumentDuplicateIcon,
  StarIcon,
  ClockIcon,
  UserIcon,
  Squares2X2Icon,
  ListBulletIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline'

// Import new components
import AssetGrid from './StyleVault/AssetGrid'
import AssetUploadModal from './StyleVault/AssetUploadModal'
import FontAssetGrid from './StyleVault/FontAssetGrid'
import FontUploadModal from './StyleVault/FontUploadModal'
import EditableRulesList from './StyleVault/EditableRulesList'

const StyleVault = ({ userId }) => {
  const { plan, hasAdvancedAnalytics } = usePlan()
  const { 
    hasFeature,
    hasPremiumAI,
    hasAdvancedAnalytics: hasAdvancedAnalyticsConditional,
    getButtonState,
    canPerformAction
  } = usePlanConditionals()
  const { showSuccess, showError } = useNotifications()

  const [styleVault, setStyleVault] = useState({
    brand_assets: {
      logos: [],
      images: [],
      color_palettes: [],
      fonts: [],
    },
    visual_guidelines: {
      primary_colors: ['#3B82F6', '#10B981'],
      secondary_colors: ['#8B5CF6', '#F59E0B'],
      brand_voice: 'professional',
      image_style: 'modern',
      typography: {
        heading_font: 'Inter',
        body_font: 'Inter',
        accent_font: 'Inter',
      },
    },
    content_templates: {
      image_prompts: {},
      content_styles: {},
      campaign_themes: [],
    },
    usage_rules: {
      dos: [
        'Use consistent color palette',
        'Maintain professional tone',
        'Include brand elements',
      ],
      donts: [
        'Avoid competitor mentions',
        'No inappropriate content',
        'Stay within brand guidelines',
      ],
    },
  })

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('brand_assets')
  const [newColorPalette, setNewColorPalette] = useState({
    name: '',
    colors: ['#000000'],
  })
  const [newImagePrompt, setNewImagePrompt] = useState({ name: '', prompt: '' })
  const [newContentStyle, setNewContentStyle] = useState({
    name: '',
    description: '',
    tone: 'professional',
  })
  const [uploadProgress, setUploadProgress] = useState({})
  const [assetSearch, setAssetSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [viewMode, setViewMode] = useState('grid') // grid or list
  const [selectedAssets, setSelectedAssets] = useState([])
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [assetFilter, setAssetFilter] = useState({ type: 'all', dateRange: 'all' })
  const [showFontUpload, setShowFontUpload] = useState(false)
  const [editingDos, setEditingDos] = useState(false)
  const [editingDonts, setEditingDonts] = useState(false)

  useEffect(() => {
    loadStyleVault()
  }, [])

  const loadStyleVault = async () => {
    try {
      setLoading(true)
      const response = await api.request('/api/user-settings/')
      const settings = response

      if (
        settings.style_vault &&
        Object.keys(settings.style_vault).length > 0
      ) {
        setStyleVault(settings.style_vault)
      } else {
        // Initialize with default structure if empty
        await saveStyleVault(styleVault)
      }
    } catch (error) {
      console.error('Failed to load Style Vault:', error)
      showError('Failed to load Style Vault data')
    } finally {
      setLoading(false)
    }
  }

  const saveStyleVault = async (vaultData = styleVault) => {
    try {
      setSaving(true)
      await api.request('/api/user-settings/', {
        method: 'PUT',
        body: { style_vault: vaultData },
      })
      setStyleVault(vaultData)
      showSuccess('Style Vault updated successfully!')
    } catch (error) {
      console.error('Failed to save Style Vault:', error)
      showError('Failed to save Style Vault changes')
    } finally {
      setSaving(false)
    }
  }

  const addColorPalette = () => {
    if (!newColorPalette.name.trim()) {
      showError('Please enter a palette name')
      return
    }

    const updatedVault = {
      ...styleVault,
      brand_assets: {
        ...styleVault.brand_assets,
        color_palettes: [
          ...styleVault.brand_assets.color_palettes,
          {
            id: Date.now(),
            name: newColorPalette.name.trim(),
            colors: newColorPalette.colors,
            created_at: new Date().toISOString(),
          },
        ],
      },
    }

    saveStyleVault(updatedVault)
    setNewColorPalette({ name: '', colors: ['#000000'] })
  }

  const removeColorPalette = (paletteId) => {
    const updatedVault = {
      ...styleVault,
      brand_assets: {
        ...styleVault.brand_assets,
        color_palettes: styleVault.brand_assets.color_palettes.filter(
          (p) => p.id !== paletteId
        ),
      },
    }
    saveStyleVault(updatedVault)
  }

  const addColorToPalette = () => {
    setNewColorPalette((prev) => ({
      ...prev,
      colors: [...prev.colors, '#000000'],
    }))
  }

  const updateColorInPalette = (index, color) => {
    setNewColorPalette((prev) => ({
      ...prev,
      colors: prev.colors.map((c, i) => (i === index ? color : c)),
    }))
  }

  const removeColorFromPalette = (index) => {
    if (newColorPalette.colors.length > 1) {
      setNewColorPalette((prev) => ({
        ...prev,
        colors: prev.colors.filter((_, i) => i !== index),
      }))
    }
  }

  const addImagePrompt = () => {
    if (!newImagePrompt.name.trim() || !newImagePrompt.prompt.trim()) {
      showError('Please fill in both name and prompt')
      return
    }

    const updatedVault = {
      ...styleVault,
      content_templates: {
        ...styleVault.content_templates,
        image_prompts: {
          ...styleVault.content_templates.image_prompts,
          [newImagePrompt.name.trim()]: newImagePrompt.prompt.trim(),
        },
      },
    }

    saveStyleVault(updatedVault)
    setNewImagePrompt({ name: '', prompt: '' })
  }

  const removeImagePrompt = (promptName) => {
    const updatedPrompts = { ...styleVault.content_templates.image_prompts }
    delete updatedPrompts[promptName]

    const updatedVault = {
      ...styleVault,
      content_templates: {
        ...styleVault.content_templates,
        image_prompts: updatedPrompts,
      },
    }

    saveStyleVault(updatedVault)
  }

  const addContentStyle = () => {
    if (!newContentStyle.name.trim() || !newContentStyle.description.trim()) {
      showError('Please fill in both name and description')
      return
    }

    const styleKey = newContentStyle.name
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
    const updatedVault = {
      ...styleVault,
      content_templates: {
        ...styleVault.content_templates,
        content_styles: {
          ...styleVault.content_templates.content_styles,
          [styleKey]: {
            name: newContentStyle.name.trim(),
            description: newContentStyle.description.trim(),
            tone: newContentStyle.tone,
            created_at: new Date().toISOString(),
          },
        },
      },
    }

    saveStyleVault(updatedVault)
    setNewContentStyle({ name: '', description: '', tone: 'professional' })
  }

  const removeContentStyle = (styleKey) => {
    const updatedStyles = { ...styleVault.content_templates.content_styles }
    delete updatedStyles[styleKey]

    const updatedVault = {
      ...styleVault,
      content_templates: {
        ...styleVault.content_templates,
        content_styles: updatedStyles,
      },
    }

    saveStyleVault(updatedVault)
  }

  const updateVisualGuidelines = (field, value) => {
    const updatedVault = {
      ...styleVault,
      visual_guidelines: {
        ...styleVault.visual_guidelines,
        [field]: value,
      },
    }
    saveStyleVault(updatedVault)
  }

  const updateUsageRules = (type, rules) => {
    const updatedVault = {
      ...styleVault,
      usage_rules: {
        ...styleVault.usage_rules,
        [type]: rules,
      },
    }
    saveStyleVault(updatedVault)
  }

  const updateTypographySetting = (field, value) => {
    const updatedVault = {
      ...styleVault,
      visual_guidelines: {
        ...styleVault.visual_guidelines,
        typography: {
          ...styleVault.visual_guidelines?.typography,
          [field]: value,
        },
      },
    }
    saveStyleVault(updatedVault)
  }

  const updatePrimaryColor = (index, color) => {
    const updatedColors = [...(styleVault.visual_guidelines?.primary_colors || [])]
    updatedColors[index] = color
    updateVisualGuidelines('primary_colors', updatedColors)
  }

  const addPrimaryColor = () => {
    const updatedColors = [...(styleVault.visual_guidelines?.primary_colors || []), '#000000']
    updateVisualGuidelines('primary_colors', updatedColors)
  }

  const removePrimaryColor = (index) => {
    const updatedColors = (styleVault.visual_guidelines?.primary_colors || []).filter((_, i) => i !== index)
    updateVisualGuidelines('primary_colors', updatedColors)
  }

  const updateSecondaryColor = (index, color) => {
    const updatedColors = [...(styleVault.visual_guidelines?.secondary_colors || [])]
    updatedColors[index] = color
    updateVisualGuidelines('secondary_colors', updatedColors)
  }

  const addSecondaryColor = () => {
    const updatedColors = [...(styleVault.visual_guidelines?.secondary_colors || []), '#000000']
    updateVisualGuidelines('secondary_colors', updatedColors)
  }

  const removeSecondaryColor = (index) => {
    const updatedColors = (styleVault.visual_guidelines?.secondary_colors || []).filter((_, i) => i !== index)
    updateVisualGuidelines('secondary_colors', updatedColors)
  }

  const handleAssetUpload = async (files, assetType, options = {}) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    formData.append('asset_type', assetType)
    
    if (options.tags) {
      formData.append('tags', JSON.stringify(options.tags))
    }

    try {
      setUploadProgress({ [assetType]: 0 })
      
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => ({
          ...prev,
          [assetType]: Math.min((prev[assetType] || 0) + Math.random() * 30, 90)
        }))
      }, 500)

      const response = await api.request('/api/style-vault/assets/', {
        method: 'POST',
        body: formData,
      })

      clearInterval(progressInterval)
      setUploadProgress({ [assetType]: 100 })

      // Update the vault with new assets
      const updatedVault = {
        ...styleVault,
        brand_assets: {
          ...styleVault.brand_assets,
          [assetType]: [...(styleVault.brand_assets?.[assetType] || []), ...response.assets],
        },
      }
      
      saveStyleVault(updatedVault)
      showSuccess(`${files.length} asset${files.length > 1 ? 's' : ''} uploaded successfully`)
      
      setTimeout(() => {
        setUploadProgress({})
      }, 2000)

    } catch (error) {
      console.error('Asset upload failed:', error)
      showError('Failed to upload assets')
      setUploadProgress({})
    }
  }

  const removeAsset = async (assetType, assetId) => {
    try {
      await api.request(`/api/style-vault/assets/${assetId}/`, {
        method: 'DELETE',
      })

      const updatedVault = {
        ...styleVault,
        brand_assets: {
          ...styleVault.brand_assets,
          [assetType]: styleVault.brand_assets?.[assetType]?.filter(asset => asset.id !== assetId) || [],
        },
      }

      saveStyleVault(updatedVault)
      showSuccess('Asset deleted successfully')
    } catch (error) {
      console.error('Failed to delete asset:', error)
      showError('Failed to delete asset')
    }
  }

  const toggleAssetSelection = (assetId) => {
    setSelectedAssets(prev => 
      prev.includes(assetId)
        ? prev.filter(id => id !== assetId)
        : [...prev, assetId]
    )
  }

  const downloadSelectedAssets = async () => {
    try {
      const response = await api.request('/api/style-vault/assets/download/', {
        method: 'POST',
        body: { asset_ids: selectedAssets },
        responseType: 'blob'
      })
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'brand-assets.zip')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      
      showSuccess('Assets downloaded successfully')
      setSelectedAssets([])
    } catch (error) {
      console.error('Failed to download assets:', error)
      showError('Failed to download assets')
    }
  }

  const deleteSelectedAssets = async () => {
    if (!window.confirm(`Delete ${selectedAssets.length} selected assets? This cannot be undone.`)) {
      return
    }

    try {
      await Promise.all(selectedAssets.map(assetId => 
        api.request(`/api/style-vault/assets/${assetId}/`, { method: 'DELETE' })
      ))

      // Remove from all asset types
      const updatedVault = {
        ...styleVault,
        brand_assets: {
          logos: styleVault.brand_assets?.logos?.filter(asset => !selectedAssets.includes(asset.id)) || [],
          images: styleVault.brand_assets?.images?.filter(asset => !selectedAssets.includes(asset.id)) || [],
          fonts: styleVault.brand_assets?.fonts?.filter(asset => !selectedAssets.includes(asset.id)) || [],
          color_palettes: styleVault.brand_assets?.color_palettes?.filter(asset => !selectedAssets.includes(asset.id)) || [],
        },
      }

      saveStyleVault(updatedVault)
      showSuccess(`${selectedAssets.length} assets deleted successfully`)
      setSelectedAssets([])
    } catch (error) {
      console.error('Failed to delete assets:', error)
      showError('Failed to delete selected assets')
    }
  }

  const handleFontUpload = async (fontData) => {
    try {
      const response = await api.request('/api/style-vault/fonts/', {
        method: 'POST',
        body: fontData,
      })

      const updatedVault = {
        ...styleVault,
        brand_assets: {
          ...styleVault.brand_assets,
          fonts: [...(styleVault.brand_assets?.fonts || []), response.font],
        },
      }

      saveStyleVault(updatedVault)
      showSuccess('Font uploaded successfully')
      setShowFontUpload(false)
    } catch (error) {
      console.error('Font upload failed:', error)
      showError('Failed to upload font')
    }
  }

  const updateFontAsset = async (fontId, updates) => {
    try {
      const response = await api.request(`/api/style-vault/fonts/${fontId}/`, {
        method: 'PATCH',
        body: updates,
      })

      const updatedVault = {
        ...styleVault,
        brand_assets: {
          ...styleVault.brand_assets,
          fonts: styleVault.brand_assets?.fonts?.map(font => 
            font.id === fontId ? { ...font, ...response.font } : font
          ) || [],
        },
      }

      saveStyleVault(updatedVault)
      showSuccess('Font updated successfully')
    } catch (error) {
      console.error('Font update failed:', error)
      showError('Failed to update font')
    }
  }

  const exportBrandGuidelines = async () => {
    try {
      const response = await api.request('/api/style-vault/export/', {
        method: 'POST',
        body: { format: 'pdf' },
        responseType: 'blob'
      })
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'brand-guidelines.pdf')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      
      showSuccess('Brand guidelines exported successfully')
    } catch (error) {
      console.error('Export failed:', error)
      showError('Failed to export brand guidelines')
    }
  }

  const tabs = [
    { id: 'brand_assets', name: 'Brand Assets', icon: SwatchIcon },
    {
      id: 'visual_guidelines',
      name: 'Visual Guidelines',
      icon: AdjustmentsHorizontalIcon,
    },
    {
      id: 'content_templates',
      name: 'Content Templates',
      icon: DocumentTextIcon,
    },
    { id: 'usage_rules', name: 'Usage Rules', icon: CheckCircleIcon },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading Style Vault...</span>
      </div>
    )
  }

  return (
    <FeatureGate
      feature="style_vault"
      mode="upgrade"
      upgradeTitle="Style Vault - Premium Feature"
      upgradeDescription="Create and manage your brand assets, color palettes, and content templates to ensure consistent styling across all your content."
      className="space-y-6"
    >
      <div className="bg-white rounded-lg shadow">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <PaintBrushIcon className="h-6 w-6 text-purple-600 mr-2" />
              <h2 className="text-lg font-medium text-gray-900">Style Vault</h2>
            </div>
            <div className="flex items-center space-x-2">
              {saving && (
                <div className="flex items-center text-sm text-gray-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                  Saving...
                </div>
              )}
              <span className="text-xs text-gray-500">
                Plan: {plan?.display_name || 'Loading...'}
              </span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 py-4 border-b border-gray-200">
          <nav className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-purple-500 text-purple-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4 mr-2" />
                  {tab.name}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'brand_assets' && (
            <div className="space-y-8">
              {/* Color Palettes */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Color Palettes
                </h3>

                {/* Existing Palettes */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {styleVault.brand_assets?.color_palettes?.map((palette) => (
                    <div
                      key={palette.id}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-gray-900">
                          {palette.name}
                        </h4>
                        <button
                          onClick={() => removeColorPalette(palette.id)}
                          className="text-red-500 hover:text-red-700"
                          aria-label={`Delete ${palette.name} palette`}
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="flex space-x-2">
                        {palette.colors.map((color, index) => (
                          <div
                            key={index}
                            className="w-8 h-8 rounded border border-gray-300"
                            style={{ backgroundColor: color }}
                            title={color}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Add New Palette */}
                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">
                    Add New Color Palette
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Palette Name
                      </label>
                      <input
                        type="text"
                        value={newColorPalette.name}
                        onChange={(e) =>
                          setNewColorPalette((prev) => ({
                            ...prev,
                            name: e.target.value,
                          }))
                        }
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        placeholder="e.g., Primary Brand Colors"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Colors
                      </label>
                      <div className="flex flex-wrap gap-2 mb-2">
                        {newColorPalette.colors.map((color, index) => (
                          <div
                            key={index}
                            className="flex items-center space-x-1"
                          >
                            <input
                              type="color"
                              value={color}
                              onChange={(e) =>
                                updateColorInPalette(index, e.target.value)
                              }
                              className="w-8 h-8 border border-gray-300 rounded cursor-pointer"
                            />
                            <button
                              onClick={() => removeColorFromPalette(index)}
                              className="text-red-500 hover:text-red-700"
                              disabled={newColorPalette.colors.length <= 1}
                            >
                              <XMarkIcon className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        <button
                          onClick={addColorToPalette}
                          className="w-8 h-8 border-2 border-dashed border-gray-300 rounded flex items-center justify-center text-gray-400 hover:text-gray-600"
                        >
                          <PlusIcon className="w-4 h-4" />
                        </button>
                      </div>
                      <button
                        onClick={addColorPalette}
                        className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                      >
                        <PlusIcon className="w-4 h-4 mr-1" />
                        Add Palette
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'visual_guidelines' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Brand Voice & Style
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Brand Voice
                    </label>
                    <select
                      value={
                        styleVault.visual_guidelines?.brand_voice ||
                        'professional'
                      }
                      onChange={(e) =>
                        updateVisualGuidelines('brand_voice', e.target.value)
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="casual">Casual</option>
                      <option value="authoritative">Authoritative</option>
                      <option value="playful">Playful</option>
                      <option value="technical">Technical</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Image Style
                    </label>
                    <select
                      value={
                        styleVault.visual_guidelines?.image_style || 'modern'
                      }
                      onChange={(e) =>
                        updateVisualGuidelines('image_style', e.target.value)
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="modern">Modern</option>
                      <option value="classic">Classic</option>
                      <option value="minimalist">Minimalist</option>
                      <option value="bold">Bold</option>
                      <option value="elegant">Elegant</option>
                      <option value="creative">Creative</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'content_templates' && (
            <div className="space-y-8">
              {/* Image Prompt Templates */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Image Prompt Templates
                </h3>

                {/* Existing Templates */}
                <div className="space-y-3 mb-6">
                  {Object.entries(
                    styleVault.content_templates?.image_prompts || {}
                  ).map(([name, prompt]) => (
                    <div
                      key={name}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{name}</h4>
                        <p className="text-sm text-gray-600 truncate">
                          {prompt}
                        </p>
                      </div>
                      <button
                        onClick={() => removeImagePrompt(name)}
                        className="text-red-500 hover:text-red-700 ml-3"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Add New Template */}
                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">
                    Add Image Prompt Template
                  </h4>
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={newImagePrompt.name}
                      onChange={(e) =>
                        setNewImagePrompt((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Template name (e.g., Product Announcement)"
                    />
                    <textarea
                      value={newImagePrompt.prompt}
                      onChange={(e) =>
                        setNewImagePrompt((prev) => ({
                          ...prev,
                          prompt: e.target.value,
                        }))
                      }
                      rows={3}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Image generation prompt template..."
                    />
                    <button
                      onClick={addImagePrompt}
                      className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded text-white bg-purple-600 hover:bg-purple-700"
                    >
                      <PlusIcon className="w-4 h-4 mr-1" />
                      Add Template
                    </button>
                  </div>
                </div>
              </div>

              {/* Content Style Templates */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Content Style Templates
                </h3>

                {/* Existing Styles */}
                <div className="space-y-3 mb-6">
                  {Object.entries(
                    styleVault.content_templates?.content_styles || {}
                  ).map(([key, style]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">
                          {style.name}
                        </h4>
                        <p className="text-sm text-gray-600">
                          {style.description}
                        </p>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mt-1">
                          {style.tone}
                        </span>
                      </div>
                      <button
                        onClick={() => removeContentStyle(key)}
                        className="text-red-500 hover:text-red-700 ml-3"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Add New Style */}
                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">
                    Add Content Style
                  </h4>
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={newContentStyle.name}
                      onChange={(e) =>
                        setNewContentStyle((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Style name (e.g., Technical Tutorial)"
                    />
                    <textarea
                      value={newContentStyle.description}
                      onChange={(e) =>
                        setNewContentStyle((prev) => ({
                          ...prev,
                          description: e.target.value,
                        }))
                      }
                      rows={2}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Describe this content style..."
                    />
                    <select
                      value={newContentStyle.tone}
                      onChange={(e) =>
                        setNewContentStyle((prev) => ({
                          ...prev,
                          tone: e.target.value,
                        }))
                      }
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="casual">Casual</option>
                      <option value="technical">Technical</option>
                      <option value="promotional">Promotional</option>
                    </select>
                    <button
                      onClick={addContentStyle}
                      className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded text-white bg-purple-600 hover:bg-purple-700"
                    >
                      <PlusIcon className="w-4 h-4 mr-1" />
                      Add Style
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'usage_rules' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2" />
                    Brand Guidelines (Do's)
                  </h3>
                  <div className="space-y-2">
                    {styleVault.usage_rules?.dos?.map((rule, index) => (
                      <div
                        key={index}
                        className="flex items-center p-2 bg-green-50 rounded"
                      >
                        <CheckCircleIcon className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" />
                        <span className="text-sm text-green-800">{rule}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <XMarkIcon className="w-5 h-5 text-red-500 mr-2" />
                    Brand Restrictions (Don'ts)
                  </h3>
                  <div className="space-y-2">
                    {styleVault.usage_rules?.donts?.map((rule, index) => (
                      <div
                        key={index}
                        className="flex items-center p-2 bg-red-50 rounded"
                      >
                        <XMarkIcon className="w-4 h-4 text-red-500 mr-2 flex-shrink-0" />
                        <span className="text-sm text-red-800">{rule}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </FeatureGate>
  )
}

export default StyleVault
