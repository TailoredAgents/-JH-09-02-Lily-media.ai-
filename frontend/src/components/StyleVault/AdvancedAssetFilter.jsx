import React, { useState, useEffect } from 'react'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  CalendarIcon,
  TagIcon,
  DocumentTextIcon,
  PhotoIcon,
  SwatchIcon,
  ChevronDownIcon,
  AdjustmentsHorizontalIcon,
  ArrowsUpDownIcon,
  Squares2X2Icon,
  ListBulletIcon,
} from '@heroicons/react/24/outline'

const ASSET_TYPES = [
  { id: 'all', label: 'All Assets', icon: Squares2X2Icon },
  { id: 'logos', label: 'Logos', icon: PhotoIcon },
  { id: 'images', label: 'Images', icon: PhotoIcon },
  { id: 'color_palettes', label: 'Color Palettes', icon: SwatchIcon },
  { id: 'fonts', label: 'Fonts', icon: DocumentTextIcon },
]

const DATE_RANGES = [
  { id: 'all', label: 'All Time' },
  { id: 'today', label: 'Today' },
  { id: 'week', label: 'This Week' },
  { id: 'month', label: 'This Month' },
  { id: 'quarter', label: 'This Quarter' },
  { id: 'year', label: 'This Year' },
]

const SORT_OPTIONS = [
  { id: 'name_asc', label: 'Name (A-Z)', field: 'name', order: 'asc' },
  { id: 'name_desc', label: 'Name (Z-A)', field: 'name', order: 'desc' },
  { id: 'date_desc', label: 'Newest First', field: 'created_at', order: 'desc' },
  { id: 'date_asc', label: 'Oldest First', field: 'created_at', order: 'asc' },
  { id: 'type_asc', label: 'Type', field: 'type', order: 'asc' },
  { id: 'size_desc', label: 'Largest First', field: 'file_size', order: 'desc' },
  { id: 'usage_desc', label: 'Most Used', field: 'usage_count', order: 'desc' },
]

const VIEW_MODES = [
  { id: 'grid', label: 'Grid View', icon: Squares2X2Icon },
  { id: 'list', label: 'List View', icon: ListBulletIcon },
]

export default function AdvancedAssetFilter({
  onFilterChange,
  onSortChange,
  onViewModeChange,
  totalAssets = 0,
  filteredCount = 0,
  availableTags = [],
  initialFilters = {},
  viewMode = 'grid',
}) {
  const [searchQuery, setSearchQuery] = useState(initialFilters.search || '')
  const [selectedType, setSelectedType] = useState(initialFilters.type || 'all')
  const [selectedDateRange, setSelectedDateRange] = useState(initialFilters.dateRange || 'all')
  const [selectedTags, setSelectedTags] = useState(initialFilters.tags || [])
  const [sortBy, setSortBy] = useState(initialFilters.sortBy || 'date_desc')
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [customDateRange, setCustomDateRange] = useState({
    start: initialFilters.customDateStart || '',
    end: initialFilters.customDateEnd || '',
  })

  // Update parent component when filters change
  useEffect(() => {
    const filters = {
      search: searchQuery,
      type: selectedType,
      dateRange: selectedDateRange,
      tags: selectedTags,
      customDateStart: customDateRange.start,
      customDateEnd: customDateRange.end,
    }
    onFilterChange?.(filters)
  }, [searchQuery, selectedType, selectedDateRange, selectedTags, customDateRange, onFilterChange])

  useEffect(() => {
    onSortChange?.(sortBy)
  }, [sortBy, onSortChange])

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value)
  }

  const handleTypeChange = (type) => {
    setSelectedType(type)
  }

  const handleTagToggle = (tag) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    )
  }

  const clearAllFilters = () => {
    setSearchQuery('')
    setSelectedType('all')
    setSelectedDateRange('all')
    setSelectedTags([])
    setCustomDateRange({ start: '', end: '' })
    setSortBy('date_desc')
  }

  const hasActiveFilters = () => {
    return searchQuery || selectedType !== 'all' || selectedDateRange !== 'all' || selectedTags.length > 0
  }

  const getActiveFilterCount = () => {
    let count = 0
    if (searchQuery) count++
    if (selectedType !== 'all') count++
    if (selectedDateRange !== 'all') count++
    if (selectedTags.length > 0) count++
    return count
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
      {/* Main Filter Bar */}
      <div className="flex flex-col lg:flex-row gap-4 mb-4">
        {/* Search Input */}
        <div className="flex-1 relative">
          <MagnifyingGlassIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search assets by name, description, or tags..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            aria-label="Search brand assets"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              aria-label="Clear search"
              type="button"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Asset Type Filter */}
        <div className="relative">
          <select
            value={selectedType}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="pl-3 pr-8 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 bg-white"
            aria-label="Filter by asset type"
          >
            {ASSET_TYPES.map(type => (
              <option key={type.id} value={type.id}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className={`inline-flex items-center px-4 py-2 border rounded-md text-sm font-medium transition-colors ${
            showAdvancedFilters || hasActiveFilters()
              ? 'border-purple-300 bg-purple-50 text-purple-700'
              : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
          }`}
          aria-expanded={showAdvancedFilters}
          aria-label="Toggle advanced filters"
          type="button"
        >
          <FunnelIcon className="h-4 w-4 mr-2" />
          Filters
          {getActiveFilterCount() > 0 && (
            <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
              {getActiveFilterCount()}
            </span>
          )}
          <ChevronDownIcon 
            className={`h-4 w-4 ml-2 transform transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`}
          />
        </button>
      </div>

      {/* Advanced Filters Panel */}
      {showAdvancedFilters && (
        <div className="border-t border-gray-200 pt-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Date Range Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date Range
              </label>
              <select
                value={selectedDateRange}
                onChange={(e) => setSelectedDateRange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              >
                {DATE_RANGES.map(range => (
                  <option key={range.id} value={range.id}>
                    {range.label}
                  </option>
                ))}
                <option value="custom">Custom Range</option>
              </select>
            </div>

            {/* Custom Date Range */}
            {selectedDateRange === 'custom' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={customDateRange.start}
                    onChange={(e) => setCustomDateRange(prev => ({ ...prev, start: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={customDateRange.end}
                    onChange={(e) => setCustomDateRange(prev => ({ ...prev, end: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
              </>
            )}

            {/* Tags Filter */}
            {availableTags.length > 0 && (
              <div className="md:col-span-2 lg:col-span-3">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <TagIcon className="h-4 w-4 inline mr-1" />
                  Filter by Tags
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableTags.map(tag => (
                    <button
                      key={tag}
                      onClick={() => handleTagToggle(tag)}
                      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                        selectedTags.includes(tag)
                          ? 'bg-purple-100 text-purple-800 border border-purple-300'
                          : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                      }`}
                      type="button"
                    >
                      {tag}
                      {selectedTags.includes(tag) && (
                        <XMarkIcon className="h-3 w-3 ml-1" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Clear Filters */}
          {hasActiveFilters() && (
            <div className="flex justify-between items-center pt-2 border-t border-gray-200">
              <button
                onClick={clearAllFilters}
                className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                type="button"
              >
                Clear All Filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* Results Summary and View Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-4 border-t border-gray-200">
        {/* Results Summary */}
        <div className="text-sm text-gray-600">
          {filteredCount !== totalAssets ? (
            <span>
              Showing <span className="font-medium">{filteredCount}</span> of{' '}
              <span className="font-medium">{totalAssets}</span> assets
            </span>
          ) : (
            <span>
              <span className="font-medium">{totalAssets}</span> asset{totalAssets !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Sort and View Controls */}
        <div className="flex items-center gap-4">
          {/* Sort Dropdown */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              aria-label="Sort assets"
            >
              {SORT_OPTIONS.map(option => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center border border-gray-300 rounded-md">
            {VIEW_MODES.map(mode => {
              const Icon = mode.icon
              return (
                <button
                  key={mode.id}
                  onClick={() => onViewModeChange?.(mode.id)}
                  className={`px-3 py-1 text-sm font-medium transition-colors ${
                    viewMode === mode.id
                      ? 'bg-purple-100 text-purple-700'
                      : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                  }`}
                  aria-label={mode.label}
                  title={mode.label}
                  type="button"
                >
                  <Icon className="h-4 w-4" />
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}