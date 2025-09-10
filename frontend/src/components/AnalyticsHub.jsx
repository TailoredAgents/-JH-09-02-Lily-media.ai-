import React, { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import apiService from '../services/api.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Date utility functions
const formatDate = (date) => {
  return date.toISOString().split('T')[0]
}

const getDateRange = (timeframe) => {
  const end = new Date()
  const start = new Date()

  switch (timeframe) {
    case '7d':
      start.setDate(end.getDate() - 7)
      break
    case '30d':
      start.setDate(end.getDate() - 30)
      break
    case '90d':
      start.setDate(end.getDate() - 90)
      break
    case '1y':
      start.setFullYear(end.getFullYear() - 1)
      break
    default:
      start.setDate(end.getDate() - 30)
  }

  return { from_date: formatDate(start), to_date: formatDate(end) }
}

// Loading Spinner Component
const LoadingSpinner = ({ darkMode }) => (
  <div
    className={`flex items-center justify-center p-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
  >
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500"></div>
    <span className="ml-2">Loading analytics...</span>
  </div>
)

// Empty State Component
const EmptyState = ({ darkMode, message = 'No data available' }) => (
  <div
    className={`flex flex-col items-center justify-center p-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
  >
    <div className="text-6xl mb-4">📊</div>
    <h3 className="text-lg font-semibold mb-2">{message}</h3>
    <p className="text-sm text-center">
      Start generating leads and quotes to see your business metrics here.
    </p>
  </div>
)

// Error State Component
const ErrorState = ({ darkMode, error, onRetry }) => (
  <div
    className={`flex flex-col items-center justify-center p-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
  >
    <div className="text-6xl mb-4">⚠️</div>
    <h3 className="text-lg font-semibold mb-2">Unable to load analytics</h3>
    <p className="text-sm text-center mb-4">
      {error || 'Something went wrong while loading your business data.'}
    </p>
    <button
      onClick={onRetry}
      className="px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors"
    >
      Try Again
    </button>
  </div>
)

// Filter Component
const FilterSection = ({ filters, setFilters, darkMode, onFilterChange }) => {
  const platforms = ['All', 'facebook', 'instagram', 'twitter']
  const timeframes = ['7d', '30d', '90d', '1y']
  const groupByOptions = [
    { value: 'day', label: 'Daily' },
    { value: 'week', label: 'Weekly' },
    { value: 'month', label: 'Monthly' },
  ]

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className={`p-6 rounded-xl backdrop-blur-md ${
        darkMode ? 'bg-gray-800/80' : 'bg-white/80'
      } border border-gray-200/20 shadow-lg`}
    >
      <h3
        className={`text-lg font-semibold mb-4 ${
          darkMode ? 'text-white' : 'text-gray-900'
        }`}
      >
        Business Analytics Filters
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Platform Filter */}
        <div>
          <label
            className={`block text-sm font-medium mb-2 ${
              darkMode ? 'text-gray-300' : 'text-gray-700'
            }`}
          >
            Platform
          </label>
          <select
            value={filters.platform}
            onChange={(e) => handleFilterChange('platform', e.target.value)}
            className={`w-full p-2 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {platforms.map((platform) => (
              <option key={platform} value={platform === 'All' ? '' : platform}>
                {platform === 'All'
                  ? 'All Platforms'
                  : platform.charAt(0).toUpperCase() + platform.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Timeframe Filter */}
        <div>
          <label
            className={`block text-sm font-medium mb-2 ${
              darkMode ? 'text-gray-300' : 'text-gray-700'
            }`}
          >
            Time Period
          </label>
          <select
            value={filters.timeframe}
            onChange={(e) => handleFilterChange('timeframe', e.target.value)}
            className={`w-full p-2 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {timeframes.map((timeframe) => (
              <option key={timeframe} value={timeframe}>
                {timeframe === '7d'
                  ? 'Last 7 days'
                  : timeframe === '30d'
                    ? 'Last 30 days'
                    : timeframe === '90d'
                      ? 'Last 90 days'
                      : 'Last year'}
              </option>
            ))}
          </select>
        </div>

        {/* Group By Filter */}
        <div>
          <label
            className={`block text-sm font-medium mb-2 ${
              darkMode ? 'text-gray-300' : 'text-gray-700'
            }`}
          >
            Group By
          </label>
          <select
            value={filters.group_by}
            onChange={(e) => handleFilterChange('group_by', e.target.value)}
            className={`w-full p-2 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {groupByOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Refresh Button */}
        <div className="flex items-end">
          <button
            onClick={() => onFilterChange(filters)}
            className="w-full px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors"
          >
            🔄 Refresh
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// Chart Container Component
const ChartContainer = ({ title, children, darkMode, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay }}
    className={`p-6 rounded-xl backdrop-blur-md ${
      darkMode ? 'bg-gray-800/80' : 'bg-white/80'
    } border border-gray-200/20 shadow-lg`}
  >
    <h3
      className={`text-lg font-semibold mb-4 ${
        darkMode ? 'text-white' : 'text-gray-900'
      }`}
    >
      {title}
    </h3>
    {children}
  </motion.div>
)

// Business KPI Metrics Component
const BusinessKPIMetrics = ({ data, darkMode, loading }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[...Array(8)].map((_, index) => (
          <div
            key={index}
            className={`p-4 rounded-xl backdrop-blur-md ${
              darkMode ? 'bg-gray-800/80' : 'bg-white/80'
            } border border-gray-200/20 shadow-lg animate-pulse`}
          >
            <div className="h-4 bg-gray-300 rounded mb-2"></div>
            <div className="h-6 bg-gray-300 rounded mb-1"></div>
            <div className="h-3 bg-gray-300 rounded"></div>
          </div>
        ))}
      </div>
    )
  }

  const totals = data?.totals || {}

  const metrics = [
    {
      label: 'Total Leads',
      value: totals.leads || 0,
      unit: '',
      icon: '👥',
      description: 'Leads generated from social media',
    },
    {
      label: 'Quotes Sent',
      value: totals.quotes || 0,
      unit: '',
      icon: '📋',
      description: 'Quotes provided to prospects',
    },
    {
      label: 'Quotes Accepted',
      value: totals.quotes_accepted || 0,
      unit: '',
      icon: '✅',
      description: 'Quotes accepted by customers',
    },
    {
      label: 'Jobs Scheduled',
      value: totals.jobs_scheduled || 0,
      unit: '',
      icon: '📅',
      description: 'Jobs scheduled from accepted quotes',
    },
    {
      label: 'Jobs Completed',
      value: totals.jobs_completed || 0,
      unit: '',
      icon: '✔️',
      description: 'Jobs successfully completed',
    },
    {
      label: 'Total Revenue',
      value: totals.revenue || 0,
      unit: '$',
      icon: '💰',
      description: 'Revenue from completed jobs',
      format: (value) => `$${value.toLocaleString()}`,
    },
    {
      label: 'Avg Ticket',
      value: totals.avg_ticket || 0,
      unit: '$',
      icon: '🎫',
      description: 'Average revenue per completed job',
      format: (value) => `$${value.toLocaleString()}`,
    },
    {
      label: 'Acceptance Rate',
      value: totals.acceptance_rate || 0,
      unit: '%',
      icon: '📈',
      description: 'Quote acceptance rate',
      format: (value) => `${(value * 100).toFixed(1)}%`,
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {metrics.map((metric, index) => (
        <motion.div
          key={metric.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: index * 0.1 }}
          className={`p-4 rounded-xl backdrop-blur-md ${
            darkMode ? 'bg-gray-800/80' : 'bg-white/80'
          } border border-gray-200/20 shadow-lg text-center group hover:scale-105 transition-transform`}
          title={metric.description}
        >
          <div className="text-2xl mb-2">{metric.icon}</div>
          <p
            className={`text-sm font-medium ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}
          >
            {metric.label}
          </p>
          <p
            className={`text-2xl font-bold mt-1 ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}
          >
            {metric.format
              ? metric.format(metric.value)
              : `${metric.unit}${metric.value.toLocaleString()}`}
          </p>
        </motion.div>
      ))}
    </div>
  )
}

// Analytics Table Component
const AnalyticsTable = ({ darkMode }) => {
  const tableData = [
    { post: 'AI Marketing Trends 2025', platform: 'LinkedIn', reach: '12.4K', engagement: '5.2%', clicks: 234 },
    { post: 'Social Media Analytics Guide', platform: 'Twitter', reach: '8.7K', engagement: '4.8%', clicks: 189 },
    { post: 'Content Automation Tips', platform: 'Instagram', reach: '15.2K', engagement: '6.1%', clicks: 312 },
    { post: 'Weekly Industry Update', platform: 'Facebook', reach: '9.3K', engagement: '3.9%', clicks: 156 },
    { post: 'AI Tools Comparison', platform: 'LinkedIn', reach: '18.6K', engagement: '7.3%', clicks: 445 }
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 1.0 }}
      className={`p-6 rounded-xl backdrop-blur-md ${
        darkMode ? 'bg-gray-800/80' : 'bg-white/80'
      } border border-gray-200/20 shadow-lg`}
    >
      <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        Top Performing Posts
      </h3>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className={`${darkMode ? 'text-gray-300' : 'text-gray-600'} text-sm`}>
              <th className="text-left pb-3">Post</th>
              <th className="text-left pb-3">Platform</th>
              <th className="text-right pb-3">Reach</th>
              <th className="text-right pb-3">Engagement</th>
              <th className="text-right pb-3">Clicks</th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, index) => (
              <tr key={index} className={`border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <td className={`py-3 ${darkMode ? 'text-white' : 'text-gray-900'} font-medium`}>{row.post}</td>
                <td className={`py-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>{row.platform}</td>
                <td className={`py-3 text-right ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{row.reach}</td>
                <td className={`py-3 text-right ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{row.engagement}</td>
                <td className={`py-3 text-right ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{row.clicks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}

// Social Metrics Component (secondary)
const SocialMetrics = ({ darkMode }) => {
  const socialMetrics = [
    {
      label: 'Total Reach',
      value: '45.2K',
      change: '+12.5%',
      positive: true,
      icon: '👀',
    },
    {
      label: 'Engagement Rate',
      value: '4.8%',
      change: '+0.3%',
      positive: true,
      icon: '❤️',
    },
    {
      label: 'Click-Through Rate',
      value: '2.1%',
      change: '-0.1%',
      positive: false,
      icon: '👆',
    },
    {
      label: 'Post Frequency',
      value: '12/week',
      change: '+2',
      positive: true,
      icon: '📝',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.8 }}
      className={`p-6 rounded-xl backdrop-blur-md ${
        darkMode ? 'bg-gray-800/80' : 'bg-white/80'
      } border border-gray-200/20 shadow-lg mb-6`}
    >
      <h3
        className={`text-lg font-semibold mb-4 ${
          darkMode ? 'text-white' : 'text-gray-900'
        }`}
      >
        Social Media Metrics
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {socialMetrics.map((metric, index) => (
          <div
            key={metric.label}
            className={`p-3 rounded-lg ${
              darkMode ? 'bg-gray-700/50' : 'bg-gray-50'
            } text-center`}
          >
            <div className="text-lg mb-1">{metric.icon}</div>
            <p
              className={`text-sm font-medium ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}
            >
              {metric.label}
            </p>
            <p
              className={`text-lg font-bold mt-1 ${
                darkMode ? 'text-white' : 'text-gray-900'
              }`}
            >
              {metric.value}
            </p>
            <p
              className={`text-xs mt-1 ${
                metric.positive ? 'text-green-500' : 'text-red-500'
              }`}
            >
              {metric.positive ? '↗️' : '↘️'} {metric.change}
            </p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

// Main Analytics Hub Component
const AnalyticsHub = ({ darkMode, searchQuery }) => {
  const [filters, setFilters] = useState({
    platform: '',
    timeframe: '30d',
    group_by: 'day',
  })

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch business analytics data
  const fetchAnalytics = async (filterParams = filters) => {
    try {
      setLoading(true)
      setError(null)

      const { from_date, to_date } = getDateRange(filterParams.timeframe)

      const params = {
        from_date,
        to_date,
        group_by: filterParams.group_by,
      }

      if (filterParams.platform) {
        params.platform = filterParams.platform
      }

      const result = await apiService.getBusinessAnalytics(params)
      setData(result)
    } catch (err) {
      console.error('Failed to fetch business analytics:', err)
      setError(err.message || 'Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  // Initial load and filter changes
  useEffect(() => {
    fetchAnalytics()
  }, [])

  const handleFilterChange = (newFilters) => {
    fetchAnalytics(newFilters)
  }

  const handleRetry = () => {
    fetchAnalytics()
  }

  // Chart options
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        labels: {
          color: darkMode ? '#ffffff' : '#000000',
        },
      },
      tooltip: {
        backgroundColor: darkMode ? '#374151' : '#ffffff',
        titleColor: darkMode ? '#ffffff' : '#000000',
        bodyColor: darkMode ? '#ffffff' : '#000000',
        borderColor: darkMode ? '#6b7280' : '#e5e7eb',
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        grid: {
          color: darkMode ? '#374151' : '#f3f4f6',
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280',
        },
      },
      y: {
        grid: {
          color: darkMode ? '#374151' : '#f3f4f6',
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280',
        },
      },
    },
  }

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: darkMode ? '#ffffff' : '#000000',
          usePointStyle: true,
          padding: 20,
        },
      },
      tooltip: {
        backgroundColor: darkMode ? '#374151' : '#ffffff',
        titleColor: darkMode ? '#ffffff' : '#000000',
        bodyColor: darkMode ? '#ffffff' : '#000000',
        borderColor: darkMode ? '#6b7280' : '#e5e7eb',
        borderWidth: 1,
      },
    },
  }

  // Prepare chart data
  const timeSeriesData = useMemo(() => {
    if (!data?.time_series?.length) return { labels: [], datasets: [] }

    const labels = data.time_series.map((point) => point.period)

    return {
      labels,
      datasets: [
        {
          label: 'Leads',
          data: data.time_series.map((point) => point.leads),
          borderColor: '#008080',
          backgroundColor: 'rgba(0, 128, 128, 0.1)',
          fill: false,
          tension: 0.4,
        },
        {
          label: 'Quotes Accepted',
          data: data.time_series.map((point) => point.quotes_accepted),
          borderColor: '#FFD700',
          backgroundColor: 'rgba(255, 215, 0, 0.1)',
          fill: false,
          tension: 0.4,
        },
        {
          label: 'Jobs Completed',
          data: data.time_series.map((point) => point.jobs_completed),
          borderColor: '#32CD32',
          backgroundColor: 'rgba(50, 205, 50, 0.1)',
          fill: false,
          tension: 0.4,
        },
      ],
    }
  }, [data])

  const platformBreakdownData = useMemo(() => {
    if (!data?.platform_breakdown?.length) return { labels: [], datasets: [] }

    return {
      labels: data.platform_breakdown.map(
        (item) => item.platform.charAt(0).toUpperCase() + item.platform.slice(1)
      ),
      datasets: [
        {
          data: data.platform_breakdown.map((item) => item.revenue),
          backgroundColor: [
            '#008080',
            '#FFD700',
            '#20B2AA',
            '#87CEEB',
            '#DDA0DD',
          ],
          borderWidth: 0,
        },
      ],
    }
  }, [data])

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1
          className={`text-3xl font-bold ${
            darkMode ? 'text-white' : 'text-gray-900'
          }`}
        >
          Business Analytics
        </h1>
        <p
          className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
        >
          Track leads, quotes, jobs, and revenue performance
        </p>
      </motion.div>

      {/* Filters */}
      <FilterSection
        filters={filters}
        setFilters={setFilters}
        darkMode={darkMode}
        onFilterChange={handleFilterChange}
      />

      {error ? (
        <ErrorState darkMode={darkMode} error={error} onRetry={handleRetry} />
      ) : (
        <>
          {/* Business KPI Metrics */}
          <BusinessKPIMetrics
            data={data}
            darkMode={darkMode}
            loading={loading}
          />

          {/* Social Metrics (Secondary) */}
          <SocialMetrics darkMode={darkMode} />

          {/* Charts Grid */}
          {loading ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {[...Array(4)].map((_, index) => (
                <ChartContainer
                  key={index}
                  title="Loading..."
                  darkMode={darkMode}
                  delay={index * 0.1}
                >
                  <LoadingSpinner darkMode={darkMode} />
                </ChartContainer>
              ))}
            </div>
          ) : !data?.totals?.leads ? (
            <EmptyState darkMode={darkMode} message="No business data yet" />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Business Pipeline Trend */}
              <ChartContainer
                title="Business Pipeline Trend"
                darkMode={darkMode}
                delay={0.2}
              >
                <div className="h-64">
                  <Line data={timeSeriesData} options={chartOptions} />
                </div>
              </ChartContainer>

              {/* Platform Revenue Distribution */}
              <ChartContainer
                title="Revenue by Platform"
                darkMode={darkMode}
                delay={0.3}
              >
                <div className="h-64">
                  {platformBreakdownData.labels.length > 0 ? (
                    <Doughnut
                      data={platformBreakdownData}
                      options={doughnutOptions}
                    />
                  ) : (
                    <EmptyState
                      darkMode={darkMode}
                      message="No platform data"
                    />
                  )}
                </div>
              </ChartContainer>

              {/* Conversion Funnel */}
              <ChartContainer
                title="Conversion Funnel"
                darkMode={darkMode}
                delay={0.4}
              >
                <div className="h-64">
                  <Bar
                    data={{
                      labels: [
                        'Leads',
                        'Quotes',
                        'Accepted',
                        'Scheduled',
                        'Completed',
                      ],
                      datasets: [
                        {
                          label: 'Count',
                          data: [
                            data?.totals?.leads || 0,
                            data?.totals?.quotes || 0,
                            data?.totals?.quotes_accepted || 0,
                            data?.totals?.jobs_scheduled || 0,
                            data?.totals?.jobs_completed || 0,
                          ],
                          backgroundColor: 'rgba(0, 128, 128, 0.8)',
                          borderRadius: 4,
                        },
                      ],
                    }}
                    options={chartOptions}
                  />
                </div>
              </ChartContainer>

              {/* Service Type Performance */}
              <ChartContainer
                title="Service Type Performance"
                darkMode={darkMode}
                delay={0.5}
              >
                <div className="h-64">
                  {data?.service_type_breakdown?.length ? (
                    <Bar
                      data={{
                        labels: data.service_type_breakdown.map((item) =>
                          item.service_type
                            .replace('_', ' ')
                            .replace(/\b\w/g, (l) => l.toUpperCase())
                        ),
                        datasets: [
                          {
                            label: 'Revenue',
                            data: data.service_type_breakdown.map(
                              (item) => item.revenue
                            ),
                            backgroundColor: 'rgba(255, 215, 0, 0.8)',
                            borderRadius: 4,
                          },
                        ],
                      }}
                      options={chartOptions}
                    />
                  ) : (
                    <EmptyState darkMode={darkMode} message="No service data" />
                  )}
                </div>
              </ChartContainer>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default AnalyticsHub
