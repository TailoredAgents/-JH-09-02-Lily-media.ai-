import React, { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Line, Bar, Doughnut, Radar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Empty state data structure - replace with API calls
const emptyData = {
  engagement: { daily: [], labels: [] },
  platforms: { data: [], labels: [] },
  contentTypes: { data: [], labels: [] },
  hourly: { data: [], labels: [] },
  viral: { reach: [], engagement: [], labels: [] },
  performance: { labels: [], datasets: [] }
}

// Filter Component
const FilterSection = ({ filters, setFilters, darkMode }) => {
  const platforms = ['All', 'LinkedIn', 'Twitter', 'Instagram', 'Facebook']
  const timeframes = ['7d', '30d', '90d', '1y']
  const metrics = ['All', 'Engagement', 'Reach', 'Clicks', 'Shares']

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className={`p-6 rounded-xl backdrop-blur-md ${
        darkMode ? 'bg-gray-800/80' : 'bg-white/80'
      } border border-gray-200/20 shadow-lg`}
    >
      <h3 className={`text-lg font-semibold mb-4 ${
        darkMode ? 'text-white' : 'text-gray-900'
      }`}>
        Analytics Filters
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Platform Filter */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            Platform
          </label>
          <select
            value={filters.platform}
            onChange={(e) => setFilters({ ...filters, platform: e.target.value })}
            className={`w-full p-2 rounded-lg border ${
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

        {/* Timeframe Filter */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            Timeframe
          </label>
          <select
            value={filters.timeframe}
            onChange={(e) => setFilters({ ...filters, timeframe: e.target.value })}
            className={`w-full p-2 rounded-lg border ${
              darkMode 
                ? 'bg-gray-700 border-gray-600 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {timeframes.map(timeframe => (
              <option key={timeframe} value={timeframe}>
                {timeframe === '7d' ? 'Last 7 days' :
                 timeframe === '30d' ? 'Last 30 days' :
                 timeframe === '90d' ? 'Last 90 days' : 'Last year'}
              </option>
            ))}
          </select>
        </div>

        {/* Metric Filter */}
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            Metric
          </label>
          <select
            value={filters.metric}
            onChange={(e) => setFilters({ ...filters, metric: e.target.value })}
            className={`w-full p-2 rounded-lg border ${
              darkMode 
                ? 'bg-gray-700 border-gray-600 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            } focus:outline-none focus:ring-2 focus:ring-teal-500`}
          >
            {metrics.map(metric => (
              <option key={metric} value={metric}>{metric}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Export Buttons */}
      <div className="flex space-x-2 mt-4">
        <button className="px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors">
          📊 Export CSV
        </button>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
          📄 Export PDF
        </button>
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
    <h3 className={`text-lg font-semibold mb-4 ${
      darkMode ? 'text-white' : 'text-gray-900'
    }`}>
      {title}
    </h3>
    {children}
  </motion.div>
)

// Key Metrics Component
const KeyMetrics = ({ darkMode }) => {
  const metrics = [
    { label: 'Total Reach', value: '45.2K', change: '+12.5%', positive: true },
    { label: 'Engagement Rate', value: '4.8%', change: '+0.3%', positive: true },
    { label: 'Click-Through Rate', value: '2.1%', change: '-0.1%', positive: false },
    { label: 'Conversions', value: '127', change: '+8.4%', positive: true }
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
          } border border-gray-200/20 shadow-lg text-center`}
        >
          <p className={`text-sm font-medium ${
            darkMode ? 'text-gray-400' : 'text-gray-600'
          }`}>
            {metric.label}
          </p>
          <p className={`text-2xl font-bold mt-1 ${
            darkMode ? 'text-white' : 'text-gray-900'
          }`}>
            {metric.value}
          </p>
          <p className={`text-sm mt-1 ${
            metric.positive ? 'text-green-500' : 'text-red-500'
          }`}>
            {metric.positive ? '↗️' : '↘️'} {metric.change}
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
    <ChartContainer title="Top Performing Content" darkMode={darkMode} delay={0.8}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className={`border-b ${
              darkMode ? 'border-gray-700' : 'border-gray-200'
            }`}>
              <th className={`text-left py-3 px-4 font-medium ${
                darkMode ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Post
              </th>
              <th className={`text-left py-3 px-4 font-medium ${
                darkMode ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Platform
              </th>
              <th className={`text-left py-3 px-4 font-medium ${
                darkMode ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Reach
              </th>
              <th className={`text-left py-3 px-4 font-medium ${
                darkMode ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Engagement
              </th>
              <th className={`text-left py-3 px-4 font-medium ${
                darkMode ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Clicks
              </th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, index) => (
              <motion.tr
                key={index}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className={`border-b ${
                  darkMode ? 'border-gray-700 hover:bg-gray-700/50' : 'border-gray-100 hover:bg-gray-50'
                } transition-colors cursor-pointer`}
              >
                <td className={`py-3 px-4 ${
                  darkMode ? 'text-white' : 'text-gray-900'
                }`}>
                  {row.post}
                </td>
                <td className={`py-3 px-4 ${
                  darkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {row.platform}
                </td>
                <td className={`py-3 px-4 ${
                  darkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {row.reach}
                </td>
                <td className={`py-3 px-4 ${
                  darkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {row.engagement}
                </td>
                <td className={`py-3 px-4 ${
                  darkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {row.clicks}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartContainer>
  )
}

// Main Analytics Hub Component
const AnalyticsHub = ({ darkMode, searchQuery }) => {
  const [filters, setFilters] = useState({
    platform: 'All',
    timeframe: '30d',
    metric: 'All'
  })

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        labels: {
          color: darkMode ? '#ffffff' : '#000000'
        }
      },
      tooltip: {
        backgroundColor: darkMode ? '#374151' : '#ffffff',
        titleColor: darkMode ? '#ffffff' : '#000000',
        bodyColor: darkMode ? '#ffffff' : '#000000',
        borderColor: darkMode ? '#6b7280' : '#e5e7eb',
        borderWidth: 1
      }
    },
    scales: {
      x: {
        grid: {
          color: darkMode ? '#374151' : '#f3f4f6'
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280'
        }
      },
      y: {
        grid: {
          color: darkMode ? '#374151' : '#f3f4f6'
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280'
        }
      }
    }
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
          padding: 20
        }
      },
      tooltip: {
        backgroundColor: darkMode ? '#374151' : '#ffffff',
        titleColor: darkMode ? '#ffffff' : '#000000',
        bodyColor: darkMode ? '#ffffff' : '#000000',
        borderColor: darkMode ? '#6b7280' : '#e5e7eb',
        borderWidth: 1
      }
    }
  }

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: darkMode ? '#ffffff' : '#000000'
        }
      },
      tooltip: {
        backgroundColor: darkMode ? '#374151' : '#ffffff',
        titleColor: darkMode ? '#ffffff' : '#000000',
        bodyColor: darkMode ? '#ffffff' : '#000000',
        borderColor: darkMode ? '#6b7280' : '#e5e7eb',
        borderWidth: 1
      }
    },
    scales: {
      r: {
        angleLines: {
          color: darkMode ? '#374151' : '#e5e7eb'
        },
        grid: {
          color: darkMode ? '#374151' : '#e5e7eb'
        },
        pointLabels: {
          color: darkMode ? '#9ca3af' : '#6b7280'
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280',
          backdropColor: 'transparent'
        }
      }
    }
  }

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
          Analytics Hub
        </h1>
        <p className={`text-lg ${
          darkMode ? 'text-gray-400' : 'text-gray-600'
        }`}>
          Deep insights into your social media performance
        </p>
      </motion.div>

      {/* Filters */}
      <FilterSection filters={filters} setFilters={setFilters} darkMode={darkMode} />

      {/* Key Metrics */}
      <KeyMetrics darkMode={darkMode} />

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Engagement Trend */}
        <ChartContainer title="Engagement Trend" darkMode={darkMode} delay={0.2}>
          <div className="h-64">
            <Line 
              data={{
                labels: emptyData.engagement.labels,
                datasets: [{
                  label: 'Engagement Rate',
                  data: emptyData.engagement.daily,
                  borderColor: '#008080',
                  backgroundColor: 'rgba(0, 128, 128, 0.1)',
                  fill: true,
                  tension: 0.4
                }]
              }} 
              options={chartOptions} 
            />
          </div>
        </ChartContainer>

        {/* Platform Performance */}
        <ChartContainer title="Platform Distribution" darkMode={darkMode} delay={0.3}>
          <div className="h-64">
            <Doughnut 
              data={{
                labels: emptyData.platforms.labels,
                datasets: [{
                  data: emptyData.platforms.data,
                  backgroundColor: ['#008080', '#FFD700', '#20B2AA', '#87CEEB', '#DDA0DD'],
                  borderWidth: 0
                }]
              }}
              options={doughnutOptions}
            />
          </div>
        </ChartContainer>

        {/* Hourly Activity */}
        <ChartContainer title="Hourly Activity Heatmap" darkMode={darkMode} delay={0.4}>
          <div className="h-64">
            <Bar 
              data={{
                labels: emptyData.hourly.labels,
                datasets: [{
                  label: 'Posts',
                  data: emptyData.hourly.data,
                  backgroundColor: 'rgba(0, 128, 128, 0.8)',
                  borderRadius: 4
                }]
              }}
              options={chartOptions}
            />
          </div>
        </ChartContainer>

        {/* Performance Radar */}
        <ChartContainer title="Performance Comparison" darkMode={darkMode} delay={0.5}>
          <div className="h-64">
            <Radar 
              data={emptyData.performance}
              options={radarOptions}
            />
          </div>
        </ChartContainer>
      </div>

      {/* Viral Content Tracking */}
      <ChartContainer title="Viral Content Tracking" darkMode={darkMode} delay={0.6}>
        <div className="h-64">
          <Line 
            data={{
              labels: emptyData.viral.labels,
              datasets: [
                {
                  label: 'Reach',
                  data: emptyData.viral.reach,
                  borderColor: '#008080',
                  backgroundColor: 'rgba(0, 128, 128, 0.1)',
                  yAxisID: 'y'
                },
                {
                  label: 'Engagement',
                  data: emptyData.viral.engagement,
                  borderColor: '#FFD700',
                  backgroundColor: 'rgba(255, 215, 0, 0.1)',
                  yAxisID: 'y1'
                }
              ]
            }}
            options={{
              ...chartOptions,
              scales: {
                ...chartOptions.scales,
                y1: {
                  type: 'linear',
                  position: 'right',
                  grid: {
                    drawOnChartArea: false,
                    color: darkMode ? '#374151' : '#f3f4f6'
                  },
                  ticks: {
                    color: darkMode ? '#9ca3af' : '#6b7280'
                  }
                }
              }
            }}
          />
        </div>
      </ChartContainer>

      {/* Analytics Table */}
      <AnalyticsTable darkMode={darkMode} />
    </div>
  )
}

export default AnalyticsHub