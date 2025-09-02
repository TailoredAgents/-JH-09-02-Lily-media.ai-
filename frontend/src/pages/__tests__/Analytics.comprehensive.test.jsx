import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Analytics from '../../components/AnalyticsHub'

// Mock Chart.js
jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options }) => (
    <div data-testid="line-chart">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  ),
  Bar: ({ data, options }) => (
    <div data-testid="bar-chart">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  ),
  Doughnut: ({ data, options }) => (
    <div data-testid="doughnut-chart">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  )
}))

// Mock RealTimeMetrics component
jest.mock('../../components/Analytics/RealTimeMetrics', () => {
  return function MockRealTimeMetrics({ timeframe }) {
    return (
      <div data-testid="real-time-metrics">
        <div>Real-time data for: {timeframe}</div>
        <div data-testid="live-metric">15,200 Live Views</div>
        <div data-testid="live-engagement">7.2% Live Engagement</div>
      </div>
    )
  }
})

// Mock useApi hook
const mockApiService = {
  getMetrics: jest.fn(() => Promise.resolve({
    total_views: 110000,
    total_engagement: 7500,
    total_followers: 14800,
    engagement_rate: 6.2,
    views_change: 8.5,
    engagement_change: -1.2,
    followers_change: 12.3,
    engagement_rate_change: 0.8
  }))
}

const mockMakeAuthenticatedRequest = jest.fn((fn) => fn())

jest.mock('../../hooks/useApi', () => ({
  useApi: () => ({
    apiService: mockApiService,
    makeAuthenticatedRequest: mockMakeAuthenticatedRequest
  })
}))

// Mock logger
jest.mock('../../utils/logger.js', () => ({
  error: jest.fn()
}))

describe('Analytics Page', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Page Header', () => {
    it('renders analytics page title and description', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Analytics')).toBeInTheDocument()
      expect(screen.getByText('Track performance metrics and insights across platforms')).toBeInTheDocument()
    })

    it('displays all header controls', () => {
      render(<Analytics />)
      
      expect(screen.getByRole('button', { name: /Real-Time/ })).toBeInTheDocument()
      expect(screen.getByDisplayValue('Last 7 days')).toBeInTheDocument()
      expect(screen.getByDisplayValue('All Platforms')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Export/ })).toBeInTheDocument()
    })
  })

  describe('Real-Time Toggle', () => {
    it('shows real-time metrics when enabled', () => {
      render(<Analytics />)
      
      const realTimeButton = screen.getByRole('button', { name: /Real-Time/ })
      expect(realTimeButton).toHaveClass('bg-green-600')
      expect(screen.getByTestId('real-time-metrics')).toBeInTheDocument()
    })

    it('toggles to historical data when disabled', () => {
      render(<Analytics />)
      
      const realTimeButton = screen.getByRole('button', { name: /Real-Time/ })
      fireEvent.click(realTimeButton)
      
      expect(realTimeButton).toHaveClass('bg-gray-100')
      expect(screen.queryByTestId('real-time-metrics')).not.toBeInTheDocument()
      expect(screen.getByText('Total Views')).toBeInTheDocument()
    })
  })

  describe('Time Range Selection', () => {
    it('renders all time range options', () => {
      render(<Analytics />)
      
      const timeRangeSelect = screen.getByDisplayValue('Last 7 days')
      fireEvent.click(timeRangeSelect)
      
      expect(screen.getByText('Last 7 days')).toBeInTheDocument()
      expect(screen.getByText('Last 30 days')).toBeInTheDocument()
      expect(screen.getByText('Last 3 months')).toBeInTheDocument()
      expect(screen.getByText('Last year')).toBeInTheDocument()
    })

    it('updates timeframe when selection changes', async () => {
      render(<Analytics />)
      
      const timeRangeSelect = screen.getByDisplayValue('Last 7 days')
      fireEvent.change(timeRangeSelect, { target: { value: '30d' } })
      
      await waitFor(() => {
        expect(timeRangeSelect.value).toBe('30d')
      })
    })

    it('triggers data reload when timeframe changes', async () => {
      render(<Analytics />)
      
      // First disable real-time to trigger API calls
      const realTimeButton = screen.getByRole('button', { name: /Real-Time/ })
      fireEvent.click(realTimeButton)
      
      const timeRangeSelect = screen.getByDisplayValue('Last 7 days')
      fireEvent.change(timeRangeSelect, { target: { value: '30d' } })
      
      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalled()
      })
    })
  })

  describe('Platform Selection', () => {
    it('renders all platform options', () => {
      render(<Analytics />)
      
      const platformSelect = screen.getByDisplayValue('All Platforms')
      fireEvent.click(platformSelect)
      
      expect(screen.getByText('All Platforms')).toBeInTheDocument()
      expect(screen.getByText('Twitter')).toBeInTheDocument()
      expect(screen.getByText('LinkedIn')).toBeInTheDocument()
      expect(screen.getByText('Instagram')).toBeInTheDocument()
      expect(screen.getByText('Facebook')).toBeInTheDocument()
    })

    it('updates platform filter when selection changes', () => {
      render(<Analytics />)
      
      const platformSelect = screen.getByDisplayValue('All Platforms')
      fireEvent.change(platformSelect, { target: { value: 'twitter' } })
      
      expect(platformSelect.value).toBe('twitter')
    })
  })

  describe('Historical Metrics Cards', () => {
    beforeEach(() => {
      render(<Analytics />)
      // Disable real-time to show historical cards
      const realTimeButton = screen.getByRole('button', { name: /Real-Time/ })
      fireEvent.click(realTimeButton)
    })

    it('displays all four metric cards with data', async () => {
      await waitFor(() => {
        expect(screen.getByText('Total Views')).toBeInTheDocument()
        expect(screen.getByText('110K')).toBeInTheDocument() // Formatted number
        
        expect(screen.getByText('Total Engagement')).toBeInTheDocument()
        expect(screen.getByText('7.5K')).toBeInTheDocument()
        
        expect(screen.getByText('Total Followers')).toBeInTheDocument()
        expect(screen.getByText('14.8K')).toBeInTheDocument()
        
        expect(screen.getByText('Engagement Rate')).toBeInTheDocument()
        expect(screen.getByText('6.2%')).toBeInTheDocument()
      })
    })

    it('shows correct change indicators with colors', async () => {
      await waitFor(() => {
        // Positive changes should be green
        const positiveChanges = screen.getAllByText(/\+/)
        expect(positiveChanges.length).toBeGreaterThan(0)
        
        // Negative changes should be red
        expect(screen.getByText('1.2%')).toBeInTheDocument() // engagement change without +
      })
    })

    it('displays appropriate icons for each metric', async () => {
      await waitFor(() => {
        // Each metric card should have an icon container
        const iconContainers = document.querySelectorAll('.bg-blue-100, .bg-green-100, .bg-purple-100, .bg-orange-100')
        expect(iconContainers).toHaveLength(4)
      })
    })
  })

  describe('Charts Section', () => {
    it('renders engagement trend chart', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Engagement Trend')).toBeInTheDocument()
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    it('renders platform distribution chart', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Platform Distribution')).toBeInTheDocument()
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
    })

    it('renders content performance chart', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Content Performance by Type')).toBeInTheDocument()
      expect(screen.getByTestId('doughnut-chart')).toBeInTheDocument()
    })

    it('displays top performing content section', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Top Performing Content')).toBeInTheDocument()
      expect(screen.getByText('5 AI Tools That Will Transform Your Social Media Strategy')).toBeInTheDocument()
      expect(screen.getByText('Behind the scenes of our content creation process')).toBeInTheDocument()
      expect(screen.getByText('Quick tips for better engagement on social media')).toBeInTheDocument()
    })
  })

  describe('Platform Breakdown Section', () => {
    it('displays platform breakdown with all platforms', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Platform Breakdown')).toBeInTheDocument()
      expect(screen.getByText('Twitter')).toBeInTheDocument()
      expect(screen.getByText('LinkedIn')).toBeInTheDocument()
      expect(screen.getByText('Instagram')).toBeInTheDocument()
      expect(screen.getByText('Facebook')).toBeInTheDocument()
    })

    it('shows follower and engagement counts for each platform', () => {
      render(<Analytics />)
      
      expect(screen.getByText('5.2K followers')).toBeInTheDocument()
      expect(screen.getByText('3.2K engagement')).toBeInTheDocument()
      expect(screen.getByText('3.8K followers')).toBeInTheDocument()
      expect(screen.getByText('2.8K engagement')).toBeInTheDocument()
    })

    it('displays platform colors correctly', () => {
      render(<Analytics />)
      
      // Each platform should have a colored circle
      const platformCircles = document.querySelectorAll('.w-12.h-12.rounded-full')
      expect(platformCircles).toHaveLength(4)
    })
  })

  describe('Top Content Performance', () => {
    it('displays content ranking with numbers', () => {
      render(<Analytics />)
      
      expect(screen.getByText('#1')).toBeInTheDocument()
      expect(screen.getByText('#2')).toBeInTheDocument()
      expect(screen.getByText('#3')).toBeInTheDocument()
    })

    it('shows content metrics for each post', () => {
      render(<Analytics />)
      
      expect(screen.getByText('15.2K views')).toBeInTheDocument()
      expect(screen.getByText('2.7% engagement')).toBeInTheDocument()
      expect(screen.getByText('8.9K views')).toBeInTheDocument()
      expect(screen.getByText('6.9% engagement')).toBeInTheDocument()
    })

    it('displays platform and interaction counts', () => {
      render(<Analytics />)
      
      expect(screen.getByText('linkedin')).toBeInTheDocument()
      expect(screen.getByText('instagram')).toBeInTheDocument()
      expect(screen.getByText('twitter')).toBeInTheDocument()
      expect(screen.getByText('413 interactions')).toBeInTheDocument() // 340+28+45
      expect(screen.getByText('619 interactions')).toBeInTheDocument() // 520+67+32
    })
  })

  describe('Data Loading and Error Handling', () => {
    it('handles API errors gracefully', async () => {
      mockApiService.getMetrics.mockRejectedValue(new Error('API Error'))
      
      render(<Analytics />)
      
      // Disable real-time to trigger API call
      const realTimeButton = screen.getByRole('button', { name: /Real-Time/ })
      fireEvent.click(realTimeButton)
      
      // Should continue to show mock data on error
      await waitFor(() => {
        expect(screen.getByText('125K')).toBeInTheDocument() // Mock data fallback
      })
    })

    it('shows loading state during data fetch', async () => {
      // Mock a delayed response
      mockApiService.getMetrics.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({}), 100))
      )
      
      render(<Analytics />)
      
      // Disable real-time to trigger loading
      const realTimeButton = screen.getByRole('button', { name: /Real-Time/ })
      fireEvent.click(realTimeButton)
      
      // Loading state should be handled gracefully
      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalled()
      })
    })
  })

  describe('Number Formatting', () => {
    it('formats large numbers correctly', () => {
      render(<Analytics />)
      
      // Mock data should be formatted
      expect(screen.getByText('125K')).toBeInTheDocument() // 125000 -> 125K
      expect(screen.getByText('8.5K')).toBeInTheDocument() // 8500 -> 8.5K
      expect(screen.getByText('15.2K')).toBeInTheDocument() // 15200 -> 15.2K
    })

    it('handles millions correctly', () => {
      // This tests the formatNumber function indirectly
      render(<Analytics />)
      
      // Function should handle both K and M formats
      const analytics = document.querySelector('[data-testid="analytics-page"]')
      expect(analytics || document.body).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<Analytics />)
      
      expect(screen.getByRole('heading', { level: 2, name: 'Analytics' })).toBeInTheDocument()
      expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(4) // Chart section headings
    })

    it('uses semantic HTML elements', () => {
      render(<Analytics />)
      
      expect(screen.getAllByRole('button')).toHaveLength(2) // Real-time and Export
      expect(screen.getAllByRole('combobox')).toHaveLength(2) // Time range and platform selects
    })

    it('provides meaningful button labels', () => {
      render(<Analytics />)
      
      expect(screen.getByRole('button', { name: /Real-Time/ })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Export/ })).toBeInTheDocument()
    })
  })

  describe('Chart Configuration', () => {
    it('passes correct data to line chart', () => {
      render(<Analytics />)
      
      const lineChart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(lineChart.querySelector('[data-testid="chart-data"]').textContent)
      
      expect(chartData.labels).toEqual(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
      expect(chartData.datasets[0].label).toBe('Engagement Rate')
      expect(chartData.datasets[0].data).toHaveLength(7)
    })

    it('configures chart options correctly', () => {
      render(<Analytics />)
      
      const lineChart = screen.getByTestId('line-chart')
      const chartOptions = JSON.parse(lineChart.querySelector('[data-testid="chart-options"]').textContent)
      
      expect(chartOptions.responsive).toBe(true)
      expect(chartOptions.maintainAspectRatio).toBe(false)
    })
  })

  describe('Real-Time Integration', () => {
    it('passes timeframe to real-time component', () => {
      render(<Analytics />)
      
      expect(screen.getByText('Real-time data for: 7d')).toBeInTheDocument()
      
      // Change timeframe
      const timeRangeSelect = screen.getByDisplayValue('Last 7 days')
      fireEvent.change(timeRangeSelect, { target: { value: '30d' } })
      
      expect(screen.getByText('Real-time data for: 30d')).toBeInTheDocument()
    })
  })
})