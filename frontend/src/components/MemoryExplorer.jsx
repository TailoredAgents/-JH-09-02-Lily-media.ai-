import React, { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useReactTable, getCoreRowModel, getFilteredRowModel, getSortedRowModel, flexRender } from '@tanstack/react-table'

// Mock memory data
const mockMemoryData = [
  {
    id: '1',
    title: 'AI Marketing Trends 2025',
    type: 'Research Article',
    content: 'Comprehensive analysis of emerging AI marketing trends including predictive analytics, personalization, and automation.',
    platform: 'LinkedIn',
    createdAt: '2025-01-15T10:30:00Z',
    engagement: 1250,
    tags: ['AI', 'Marketing', 'Trends', '2025'],
    similarity: 95,
    status: 'Published',
    repurposeCount: 3
  },
  {
    id: '2',
    title: 'Social Media Analytics Calculator',
    type: 'Tool/Resource',
    content: 'Interactive calculator helping businesses measure their social media performance with detailed engagement and reach metrics.',
    platform: 'Twitter',
    createdAt: '2025-01-14T15:45:00Z',
    engagement: 890,
    tags: ['Analytics', 'Calculator', 'Metrics', 'Business'],
    similarity: 87,
    status: 'Draft',
    repurposeCount: 1
  },
  {
    id: '3',
    title: 'Content Automation Best Practices',
    type: 'Guide',
    content: 'Step-by-step guide on implementing content automation without losing the human touch.',
    platform: 'Instagram',
    createdAt: '2025-01-13T09:15:00Z',
    engagement: 2100,
    tags: ['Automation', 'Content', 'Best Practices'],
    similarity: 92,
    status: 'Published',
    repurposeCount: 5
  },
  {
    id: '4',
    title: 'Industry Weekly Digest',
    type: 'Newsletter',
    content: 'Weekly roundup of social media marketing news, updates, and industry insights.',
    platform: 'Facebook',
    createdAt: '2025-01-12T16:20:00Z',
    engagement: 650,
    tags: ['Newsletter', 'Industry', 'Weekly', 'News'],
    similarity: 78,
    status: 'Archived',
    repurposeCount: 2
  },
  {
    id: '5',
    title: 'Video Marketing Statistics',
    type: 'Data Report',
    content: 'Latest statistics and trends in video marketing across all major social platforms.',
    platform: 'Facebook',
    createdAt: '2025-01-11T11:00:00Z',
    engagement: 3400,
    tags: ['Video', 'Marketing', 'Statistics', 'Report'],
    similarity: 89,
    status: 'Published',
    repurposeCount: 4
  },
  {
    id: '6',
    title: 'Influencer Collaboration Guide',
    type: 'Guide',
    content: 'Complete guide to finding, vetting, and collaborating with influencers for maximum impact.',
    platform: 'LinkedIn',
    createdAt: '2025-01-10T14:30:00Z',
    engagement: 1800,
    tags: ['Influencer', 'Collaboration', 'Marketing'],
    similarity: 85,
    status: 'Published',
    repurposeCount: 3
  }
]

// Content Detail Modal Component
const ContentDetailModal = ({ content, isOpen, onClose, darkMode }) => {
  if (!isOpen || !content) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className={`max-w-2xl w-full max-h-[80vh] overflow-y-auto rounded-xl ${
          darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'
        } p-6`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold mb-2">{content.title}</h2>
            <div className="flex items-center space-x-4 text-sm">
              <span className={`px-2 py-1 rounded-full ${
                content.type === 'Research Article' ? 'bg-blue-100 text-blue-800' :
                content.type === 'Guide' ? 'bg-green-100 text-green-800' :
                content.type === 'Tool/Resource' ? 'bg-purple-100 text-purple-800' :
                content.type === 'Newsletter' ? 'bg-yellow-100 text-yellow-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {content.type}
              </span>
              <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                {content.platform}
              </span>
              <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                {new Date(content.createdAt).toLocaleDateString()}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`text-2xl ${
              darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">Content</h3>
          <p className={`leading-relaxed ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            {content.content}
          </p>
        </div>

        {/* Tags */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">Tags</h3>
          <div className="flex flex-wrap gap-2">
            {content.tags.map((tag, index) => (
              <span
                key={index}
                className="px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm"
              >
                #{tag}
              </span>
            ))}
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className={`p-3 rounded-lg ${
            darkMode ? 'bg-gray-700' : 'bg-gray-100'
          } text-center`}>
            <p className="text-2xl font-bold text-teal-600">{content.engagement}</p>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Engagement
            </p>
          </div>
          <div className={`p-3 rounded-lg ${
            darkMode ? 'bg-gray-700' : 'bg-gray-100'
          } text-center`}>
            <p className="text-2xl font-bold text-yellow-600">{content.similarity}%</p>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Similarity
            </p>
          </div>
          <div className={`p-3 rounded-lg ${
            darkMode ? 'bg-gray-700' : 'bg-gray-100'
          } text-center`}>
            <p className="text-2xl font-bold text-purple-600">{content.repurposeCount}</p>
            <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Repurposed
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-3">
          <button className="flex-1 px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors">
            🔄 Repurpose Content
          </button>
          <button className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
            📝 Edit Content
          </button>
          <button className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors">
            📊 View Analytics
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// Search and Filter Component
const SearchFilters = ({ globalFilter, setGlobalFilter, typeFilter, setTypeFilter, platformFilter, setPlatformFilter, darkMode }) => {
  const types = ['All', 'Research Article', 'Guide', 'Tool/Resource', 'Newsletter', 'Data Report']
  const platforms = ['All', 'LinkedIn', 'Twitter', 'Instagram', 'Facebook']

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className={`p-6 rounded-xl backdrop-blur-md ${
        darkMode ? 'bg-gray-800/80' : 'bg-white/80'
      } border border-gray-200/20 shadow-lg`}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Semantic Search */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            🧠 Semantic Search
          </label>
          <input
            type="text"
            placeholder="Search by content, topics, or concepts..."
            value={globalFilter || ''}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className={`w-full p-3 rounded-lg border ${
              darkMode 
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent`}
          />
        </div>

        {/* Content Type Filter */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            Content Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className={`w-full p-3 rounded-lg border ${
              darkMode 
                ? 'bg-gray-700 border-gray-600 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {types.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>

        {/* Platform Filter */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            Platform
          </label>
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className={`w-full p-3 rounded-lg border ${
              darkMode 
                ? 'bg-gray-700 border-gray-600 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {platforms.map(platform => (
              <option key={platform} value={platform}>{platform}</option>
            ))}
          </select>
        </div>
      </div>
    </motion.div>
  )
}

// Main Memory Explorer Component
const MemoryExplorer = ({ darkMode, searchQuery }) => {
  const [selectedContent, setSelectedContent] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [globalFilter, setGlobalFilter] = useState(searchQuery || '')
  const [typeFilter, setTypeFilter] = useState('All')
  const [platformFilter, setPlatformFilter] = useState('All')

  // Filter data based on filters
  const filteredData = useMemo(() => {
    return mockMemoryData.filter(item => {
      const matchesType = typeFilter === 'All' || item.type === typeFilter
      const matchesPlatform = platformFilter === 'All' || item.platform === platformFilter
      const matchesSearch = !globalFilter || 
        item.title.toLowerCase().includes(globalFilter.toLowerCase()) ||
        item.content.toLowerCase().includes(globalFilter.toLowerCase()) ||
        item.tags.some(tag => tag.toLowerCase().includes(globalFilter.toLowerCase()))
      
      return matchesType && matchesPlatform && matchesSearch
    })
  }, [typeFilter, platformFilter, globalFilter])

  // Table columns
  const columns = useMemo(() => [
    {
      accessorKey: 'title',
      header: 'Title',
      cell: ({ row }) => (
        <div>
          <p className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            {row.original.title}
          </p>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {row.original.type}
          </p>
        </div>
      )
    },
    {
      accessorKey: 'platform',
      header: 'Platform',
      cell: ({ getValue }) => (
        <span className={`px-2 py-1 rounded-full text-xs ${
          getValue() === 'LinkedIn' ? 'bg-blue-100 text-blue-800' :
          getValue() === 'Twitter' ? 'bg-sky-100 text-sky-800' :
          getValue() === 'Instagram' ? 'bg-pink-100 text-pink-800' :
          getValue() === 'Facebook' ? 'bg-indigo-100 text-indigo-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {getValue()}
        </span>
      )
    },
    {
      accessorKey: 'createdAt',
      header: 'Created',
      cell: ({ getValue }) => new Date(getValue()).toLocaleDateString()
    },
    {
      accessorKey: 'engagement',
      header: 'Engagement',
      cell: ({ getValue }) => getValue().toLocaleString()
    },
    {
      accessorKey: 'similarity',
      header: 'Similarity',
      cell: ({ getValue }) => (
        <div className="flex items-center space-x-2">
          <div className={`w-full bg-gray-200 rounded-full h-2`}>
            <div
              className={`h-2 rounded-full ${
                getValue() >= 90 ? 'bg-green-500' :
                getValue() >= 80 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${getValue()}%` }}
            />
          </div>
          <span className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            {getValue()}%
          </span>
        </div>
      )
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ getValue }) => (
        <span className={`px-2 py-1 rounded-full text-xs ${
          getValue() === 'Published' ? 'bg-green-100 text-green-800' :
          getValue() === 'Draft' ? 'bg-yellow-100 text-yellow-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {getValue()}
        </span>
      )
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex space-x-2">
          <button
            onClick={() => {
              setSelectedContent(row.original)
              setIsModalOpen(true)
            }}
            className="px-3 py-1 bg-teal-500 text-white rounded text-xs hover:bg-teal-600 transition-colors"
          >
            View
          </button>
          <button className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600 transition-colors">
            Repurpose
          </button>
        </div>
      )
    }
  ], [darkMode])

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    globalFilter,
    onGlobalFilterChange: setGlobalFilter
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className={`text-3xl font-bold ${
          darkMode ? 'text-white' : 'text-gray-900'
        }`}>
          Memory Explorer
        </h1>
        <p className={`text-lg ${
          darkMode ? 'text-gray-400' : 'text-gray-600'
        }`}>
          Search and explore your content archive with AI-powered insights
        </p>
      </motion.div>

      {/* Search and Filters */}
      <SearchFilters
        globalFilter={globalFilter}
        setGlobalFilter={setGlobalFilter}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
        platformFilter={platformFilter}
        setPlatformFilter={setPlatformFilter}
        darkMode={darkMode}
      />

      {/* Memory Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Items', value: mockMemoryData.length, icon: '📚' },
          { label: 'Published', value: mockMemoryData.filter(item => item.status === 'Published').length, icon: '✅' },
          { label: 'Ready to Repurpose', value: mockMemoryData.filter(item => item.similarity > 85).length, icon: '🔄' },
          { label: 'High Engagement', value: mockMemoryData.filter(item => item.engagement > 1500).length, icon: '🚀' }
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: index * 0.1 }}
            className={`p-4 rounded-xl backdrop-blur-md ${
              darkMode ? 'bg-gray-800/80' : 'bg-white/80'
            } border border-gray-200/20 shadow-lg text-center`}
          >
            <div className="text-2xl mb-2">{stat.icon}</div>
            <p className={`text-2xl font-bold ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}>
              {stat.value}
            </p>
            <p className={`text-sm ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}>
              {stat.label}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Memory Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className={`rounded-xl backdrop-blur-md ${
          darkMode ? 'bg-gray-800/80' : 'bg-white/80'
        } border border-gray-200/20 shadow-lg overflow-hidden`}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={`${
              darkMode ? 'bg-gray-700/50' : 'bg-gray-50/50'
            }`}>
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <th
                      key={header.id}
                      className={`px-6 py-4 text-left text-sm font-semibold ${
                        darkMode ? 'text-gray-300' : 'text-gray-700'
                      } cursor-pointer hover:bg-gray-100/10`}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center space-x-2">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() && (
                          <span>{header.column.getIsSorted() === 'desc' ? '↓' : '↑'}</span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row, index) => (
                <motion.tr
                  key={row.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4, delay: index * 0.05 }}
                  className={`border-t ${
                    darkMode 
                      ? 'border-gray-700 hover:bg-gray-700/30' 
                      : 'border-gray-200 hover:bg-gray-50/50'
                  } transition-colors cursor-pointer`}
                  onClick={() => {
                    setSelectedContent(row.original)
                    setIsModalOpen(true)
                  }}
                >
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-6 py-4">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Table Footer */}
        <div className={`px-6 py-4 border-t ${
          darkMode ? 'border-gray-700' : 'border-gray-200'
        }`}>
          <p className={`text-sm ${
            darkMode ? 'text-gray-400' : 'text-gray-600'
          }`}>
            Showing {filteredData.length} of {mockMemoryData.length} items
          </p>
        </div>
      </motion.div>

      {/* Content Detail Modal */}
      <ContentDetailModal
        content={selectedContent}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedContent(null)
        }}
        darkMode={darkMode}
      />
    </div>
  )
}

export default MemoryExplorer