import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { usePlan } from '../contexts/PlanContext'
import api from '../services/api'
import PlanGate from '../components/PlanGate'
import { FeatureGate } from '../components/enhanced/EnhancedPlanGate'
import {
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CheckIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  UserIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
  CurrencyDollarIcon,
  BuildingOffice2Icon,
  PhoneIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline'
import {
  CheckCircleIcon as CheckCircleIconSolid,
  XCircleIcon as XCircleIconSolid,
  ExclamationCircleIcon as ExclamationCircleIconSolid,
} from '@heroicons/react/24/solid'

const statusColors = {
  // Lead statuses
  new: 'bg-blue-100 text-blue-800 border-blue-200',
  contacted: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  qualified: 'bg-green-100 text-green-800 border-green-200',
  unqualified: 'bg-red-100 text-red-800 border-red-200',
  converted: 'bg-purple-100 text-purple-800 border-purple-200',
  
  // Quote statuses
  draft: 'bg-gray-100 text-gray-800 border-gray-200',
  sent: 'bg-blue-100 text-blue-800 border-blue-200',
  viewed: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  accepted: 'bg-green-100 text-green-800 border-green-200',
  rejected: 'bg-red-100 text-red-800 border-red-200',
  expired: 'bg-gray-100 text-gray-800 border-gray-200',
  
  // Job statuses
  scheduled: 'bg-blue-100 text-blue-800 border-blue-200',
  in_progress: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  completed: 'bg-green-100 text-green-800 border-green-200',
  cancelled: 'bg-red-100 text-red-800 border-red-200',
  rescheduled: 'bg-orange-100 text-orange-800 border-orange-200',
}

const priorityColors = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-green-100 text-green-800',
}

function SocialInbox() {
  const { user } = useAuth()
  const { hasAIInbox } = usePlan()

  const [activeTab, setActiveTab] = useState('leads') // 'leads', 'quotes', 'jobs'
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState(null)

  // Filters
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [serviceTypeFilter, setServiceTypeFilter] = useState('all')

  // Pagination and stats
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [stats, setStats] = useState({})

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const params = {
        page,
        per_page: 20,
        search: searchTerm || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        service_type: serviceTypeFilter !== 'all' ? serviceTypeFilter : undefined,
      }

      let response
      switch (activeTab) {
        case 'leads':
          response = await api.getLeads(params)
          break
        case 'quotes':
          response = await api.getQuotes(params)
          break
        case 'jobs':
          response = await api.getJobs(params)
          break
        default:
          throw new Error('Invalid tab')
      }
      
      setData(response.data || response.items || [])
      setTotalPages(response.pagination?.total_pages || Math.ceil((response.total || 0) / 20))
      setStats(response.stats || response.summary || {})
    } catch (error) {
      console.error(`Failed to fetch ${activeTab}:`, error)
      setData([])
    } finally {
      setLoading(false)
    }
  }, [page, searchTerm, statusFilter, serviceTypeFilter, activeTab])

  useEffect(() => {
    setPage(1) // Reset page when changing tabs
    setSelectedItem(null)
  }, [activeTab])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleItemSelect = useCallback((item) => {
    setSelectedItem(item)
  }, [])

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now - date) / (1000 * 60 * 60))

    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours}h ago`
    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays < 30) return `${diffInDays}d ago`
    return date.toLocaleDateString()
  }

  const formatCurrency = (amount) => {
    if (!amount) return '$0'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  const getStatusOptions = () => {
    switch (activeTab) {
      case 'leads':
        return [
          { value: 'all', label: 'All Status' },
          { value: 'new', label: 'New' },
          { value: 'contacted', label: 'Contacted' },
          { value: 'qualified', label: 'Qualified' },
          { value: 'unqualified', label: 'Unqualified' },
          { value: 'converted', label: 'Converted' },
        ]
      case 'quotes':
        return [
          { value: 'all', label: 'All Status' },
          { value: 'draft', label: 'Draft' },
          { value: 'sent', label: 'Sent' },
          { value: 'viewed', label: 'Viewed' },
          { value: 'accepted', label: 'Accepted' },
          { value: 'rejected', label: 'Rejected' },
          { value: 'expired', label: 'Expired' },
        ]
      case 'jobs':
        return [
          { value: 'all', label: 'All Status' },
          { value: 'scheduled', label: 'Scheduled' },
          { value: 'in_progress', label: 'In Progress' },
          { value: 'completed', label: 'Completed' },
          { value: 'cancelled', label: 'Cancelled' },
          { value: 'rescheduled', label: 'Rescheduled' },
        ]
      default:
        return []
    }
  }

  const getStatsCards = () => {
    switch (activeTab) {
      case 'leads':
        return [
          { label: 'Total Leads', value: stats.total || 0, icon: '👥', color: 'bg-blue-50' },
          { label: 'New Leads', value: stats.new || 0, icon: '🆕', color: 'bg-blue-50' },
          { label: 'Qualified', value: stats.qualified || 0, icon: '✅', color: 'bg-green-50' },
          { label: 'Converted', value: stats.converted || 0, icon: '💰', color: 'bg-purple-50' },
        ]
      case 'quotes':
        return [
          { label: 'Total Quotes', value: stats.total || 0, icon: '📋', color: 'bg-blue-50' },
          { label: 'Sent', value: stats.sent || 0, icon: '📤', color: 'bg-blue-50' },
          { label: 'Accepted', value: stats.accepted || 0, icon: '✅', color: 'bg-green-50' },
          { label: 'Total Value', value: formatCurrency(stats.total_value), icon: '💰', color: 'bg-green-50' },
        ]
      case 'jobs':
        return [
          { label: 'Total Jobs', value: stats.total || 0, icon: '🔧', color: 'bg-blue-50' },
          { label: 'Scheduled', value: stats.scheduled || 0, icon: '📅', color: 'bg-blue-50' },
          { label: 'Completed', value: stats.completed || 0, icon: '✅', color: 'bg-green-50' },
          { label: 'Revenue', value: formatCurrency(stats.revenue), icon: '💰', color: 'bg-green-50' },
        ]
      default:
        return []
    }
  }

  const renderItemCard = (item) => {
    const commonClasses = `p-4 cursor-pointer hover:bg-gray-50 ${
      selectedItem?.id === item.id
        ? 'bg-blue-50 border-r-2 border-blue-500'
        : ''
    }`

    switch (activeTab) {
      case 'leads':
        return (
          <div
            key={item.id}
            className={commonClasses}
            onClick={() => handleItemSelect(item)}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-2">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${
                      statusColors[item.status] || statusColors.new
                    }`}
                  >
                    {item.status}
                  </span>
                  {item.platform && (
                    <span className="text-xs text-gray-500 capitalize">
                      {item.platform}
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2 mb-2">
                  <UserIcon className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">
                    {item.name || item.customer_name || 'Unknown'}
                  </span>
                  {item.email && (
                    <>
                      <EnvelopeIcon className="h-4 w-4 text-gray-400 ml-2" />
                      <span className="text-xs text-gray-600">{item.email}</span>
                    </>
                  )}
                </div>

                {item.notes && (
                  <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                    {item.notes}
                  </p>
                )}

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>
                    {formatTimeAgo(item.created_at)}
                  </span>
                  {item.estimated_value && (
                    <span className="font-medium">
                      {formatCurrency(item.estimated_value)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )

      case 'quotes':
        return (
          <div
            key={item.id}
            className={commonClasses}
            onClick={() => handleItemSelect(item)}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-2">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${
                      statusColors[item.status] || statusColors.draft
                    }`}
                  >
                    {item.status}
                  </span>
                  {item.service_type && (
                    <span className="text-xs text-gray-500 capitalize">
                      {item.service_type.replace('_', ' ')}
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2 mb-2">
                  <UserIcon className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">
                    {item.customer_name || item.customer_email || 'Unknown'}
                  </span>
                  <CurrencyDollarIcon className="h-4 w-4 text-gray-400 ml-2" />
                  <span className="text-sm font-semibold text-gray-900">
                    {formatCurrency(item.total_amount)}
                  </span>
                </div>

                {item.address && (
                  <div className="flex items-center space-x-2 mb-2">
                    <BuildingOffice2Icon className="h-4 w-4 text-gray-400" />
                    <span className="text-xs text-gray-600 line-clamp-1">
                      {item.address}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>
                    {formatTimeAgo(item.created_at)}
                  </span>
                  {item.valid_until && (
                    <span>
                      Expires: {new Date(item.valid_until).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )

      case 'jobs':
        return (
          <div
            key={item.id}
            className={commonClasses}
            onClick={() => handleItemSelect(item)}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-2">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${
                      statusColors[item.status] || statusColors.scheduled
                    }`}
                  >
                    {item.status}
                  </span>
                  {item.service_type && (
                    <span className="text-xs text-gray-500 capitalize">
                      {item.service_type.replace('_', ' ')}
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2 mb-2">
                  <UserIcon className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">
                    {item.customer_name || 'Unknown'}
                  </span>
                  <CurrencyDollarIcon className="h-4 w-4 text-gray-400 ml-2" />
                  <span className="text-sm font-semibold text-gray-900">
                    {formatCurrency(item.actual_cost || item.estimated_cost)}
                  </span>
                </div>

                {item.address && (
                  <div className="flex items-center space-x-2 mb-2">
                    <BuildingOffice2Icon className="h-4 w-4 text-gray-400" />
                    <span className="text-xs text-gray-600 line-clamp-1">
                      {item.address}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between text-xs text-gray-500">
                  {item.scheduled_for ? (
                    <div className="flex items-center">
                      <CalendarDaysIcon className="h-4 w-4 mr-1" />
                      <span>
                        {new Date(item.scheduled_for).toLocaleDateString()}
                      </span>
                    </div>
                  ) : (
                    <span>
                      {formatTimeAgo(item.created_at)}
                    </span>
                  )}
                  {item.duration_minutes && (
                    <span>
                      {Math.round(item.duration_minutes / 60)}h job
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  const renderItemDetails = () => {
    if (!selectedItem) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <DocumentTextIcon className="h-12 w-12 mx-auto mb-4" />
            <p className="text-lg font-medium mb-2">
              Select a {activeTab.slice(0, -1)}
            </p>
            <p>
              Choose a {activeTab.slice(0, -1)} from the list to view details
            </p>
          </div>
        </div>
      )
    }

    return (
      <div className="flex-1 flex flex-col bg-gray-50">
        <div className="bg-white border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-3">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    {selectedItem.customer_name || selectedItem.name || selectedItem.customer_email || 'Unknown'}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {activeTab.slice(0, -1).toUpperCase()} #{selectedItem.id}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-4 text-sm text-gray-500 mb-4">
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${
                    statusColors[selectedItem.status] || statusColors.new
                  }`}
                >
                  {selectedItem.status}
                </span>
                {selectedItem.service_type && (
                  <span className="capitalize">
                    {selectedItem.service_type.replace('_', ' ')}
                  </span>
                )}
                <span>
                  {formatTimeAgo(selectedItem.created_at)}
                </span>
              </div>
            </div>

            <button
              onClick={() => setSelectedItem(null)}
              className="text-gray-400 hover:text-gray-500"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {selectedItem.customer_email && (
              <div className="flex items-center space-x-2">
                <EnvelopeIcon className="h-4 w-4 text-gray-400" />
                <span className="text-sm">{selectedItem.customer_email}</span>
              </div>
            )}
            {selectedItem.customer_phone && (
              <div className="flex items-center space-x-2">
                <PhoneIcon className="h-4 w-4 text-gray-400" />
                <span className="text-sm">{selectedItem.customer_phone}</span>
              </div>
            )}
            {selectedItem.address && (
              <div className="flex items-center space-x-2">
                <BuildingOffice2Icon className="h-4 w-4 text-gray-400" />
                <span className="text-sm">{selectedItem.address}</span>
              </div>
            )}
            {(selectedItem.total_amount || selectedItem.estimated_cost || selectedItem.actual_cost) && (
              <div className="flex items-center space-x-2">
                <CurrencyDollarIcon className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-semibold">
                  {formatCurrency(
                    selectedItem.total_amount || 
                    selectedItem.actual_cost || 
                    selectedItem.estimated_cost
                  )}
                </span>
              </div>
            )}
          </div>

          {(selectedItem.notes || selectedItem.description) && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Notes</h4>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {selectedItem.notes || selectedItem.description}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  const getTabTitle = (tab) => {
    switch (tab) {
      case 'leads':
        return 'Leads'
      case 'quotes':
        return 'Quotes'
      case 'jobs':
        return 'Jobs'
      default:
        return tab
    }
  }

  return (
    <FeatureGate
      feature="ai_inbox"
      mode="upgrade"
      upgradeTitle="Business Management - Premium Feature"
      upgradeDescription="Access comprehensive lead, quote, and job management with advanced filtering, analytics, and business workflow tools"
      fallbackMode="upgrade-page"
      className="min-h-screen bg-gray-50"
    >
      <div className="h-screen flex flex-col">
        {/* Tab Navigation */}
        <div className="bg-white border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
            {['leads', 'quotes', 'jobs'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <DocumentTextIcon className="h-5 w-5 inline mr-2" />
                {getTabTitle(tab)}
                {stats.total > 0 && (
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                    {stats.total}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Header with stats and filters */}
        <div className="bg-white shadow-sm border-b border-gray-200 p-6">
          {/* Stats cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {getStatsCards().map((stat, index) => (
              <div key={index} className={`${stat.color} rounded-lg p-4`}>
                <div className="flex items-center">
                  <div className="text-2xl mr-3">{stat.icon}</div>
                  <div>
                    <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                    <p className="text-2xl font-semibold text-gray-900">
                      {stat.value}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Search and filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder={`Search ${activeTab}...`}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <select
              className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {getStatusOptions().map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            {(activeTab === 'quotes' || activeTab === 'jobs') && (
              <select
                className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                value={serviceTypeFilter}
                onChange={(e) => setServiceTypeFilter(e.target.value)}
              >
                <option value="all">All Services</option>
                <option value="pressure_washing">Pressure Washing</option>
                <option value="soft_wash">Soft Wash</option>
                <option value="deck_cleaning">Deck Cleaning</option>
                <option value="concrete_cleaning">Concrete Cleaning</option>
                <option value="gutter_cleaning">Gutter Cleaning</option>
              </select>
            )}

            <button
              onClick={fetchData}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <ArrowPathIcon className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 flex overflow-hidden">
          {/* List */}
          <div className="w-1/2 bg-white border-r border-gray-200 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              </div>
            ) : data.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-center">
                <div>
                  <DocumentTextIcon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No {activeTab} found
                  </h3>
                  <p className="text-gray-500">
                    Get started by creating your first {activeTab.slice(0, -1)} or adjust your filters.
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {data.map((item) => renderItemCard(item))}
              </div>
            )}
          </div>

          {/* Details panel */}
          {renderItemDetails()}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-white border-t border-gray-200 px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Page {page} of {totalPages}
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() =>
                    setPage((p) => Math.min(totalPages, p + 1))
                  }
                  disabled={page === totalPages}
                  className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </FeatureGate>
  )
}

export default SocialInbox