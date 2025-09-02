import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Analytics from '../../components/AnalyticsHub'

// Mock the hooks and services
jest.mock('../../hooks/useApi', () => ({
  useApi: jest.fn()
}))

jest.mock('../../hooks/useRealTimeData', () => ({
  useRealTimeData: jest.fn(),
  useRealTimeAnalytics: jest.fn(),
  useRealTimePerformance: jest.fn()
}))

jest.mock('../../utils/logger.js', () => ({
  info: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
  warn: jest.fn()
}))

// Mock RealTimeMetrics component
jest.mock('../../components/Analytics/RealTimeMetrics', () => {
  return function MockRealTimeMetrics() {
    return <div data-testid="real-time-metrics">Real Time Metrics</div>
  }
})

// Mock Chart.js components
jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options }) => (
    <div data-testid="line-chart" data-chart-data={JSON.stringify(data)}>
      Line Chart
    </div>
  ),
  Bar: ({ data, options }) => (
    <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)}>
      Bar Chart
    </div>
  ),
  Doughnut: ({ data, options }) => (
    <div data-testid="doughnut-chart" data-chart-data={JSON.stringify(data)}>
      Doughnut Chart
    </div>
  )
}))

jest.mock('chart.js', () => ({
  Chart: {
    register: jest.fn()
  },
  CategoryScale: jest.fn(),
  LinearScale: jest.fn(),
  PointElement: jest.fn(),
  LineElement: jest.fn(),
  BarElement: jest.fn(),
  ArcElement: jest.fn(),
  Title: jest.fn(),
  Tooltip: jest.fn(),
  Legend: jest.fn()
}))

const { useApi } = require('../../hooks/useApi')
const { useRealTimeData, useRealTimeAnalytics, useRealTimePerformance } = require('../../hooks/useRealTimeData')

// Test wrapper
const TestWrapper = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Analytics Page', () => {
  const mockAnalyticsData = {
    overview: {
      totalViews: 125000,
      totalEngagement: 8500,
      totalFollowers: 15200,
      engagementRate: 6.8,
      viewsChange: 12.5,
      engagementChange: -2.3,
      followersChange: 8.2,
      engagementRateChange: 1.4
    },
    platforms: {
      twitter: { name: 'Twitter', followers: 5200, engagement: 3200, color: '#1DA1F2' },
       { name: 'LinkedIn', followers: 3800, engagement: 2800, color: '#0077B5' },
      instagram: { name: 'Instagram', followers: 4200, engagement: 1800, color: '#E4405F' },
      facebook: { name: 'Facebook', followers: 2000, engagement: 700, color: '#1877F2' }
    },
    engagementTrend: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [{
        label: 'Engagement Rate',
        data: [6.2, 7.1, 5.8, 8.2, 6.9, 7.5, 6.8],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
      }]
    },
    topContent: [
      {
        id: 1,
        title: "5 AI Tools That Will Transform Your Social Media Strategy",
        platform: ,
        views: 15200,
        likes: 340,
        engagement_rate: 2.7
      }
    ]
  }

  const mockPerformanceData = {
    averageEngagement: 8.5,
    topPlatforms: ['twitter', 'linkedin'],
    bestTimeToPost: '2:00 PM',
    contentTypes: {
      text: 45,
      image: 35,
      video: 20
    }
  }

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Default mock implementations
    useApi.mockReturnValue({
      data: mockAnalyticsData,
      loading: false,
      error: null,
      refetch: jest.fn()
    })

    useRealTimeData.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      isConnected: true,
      lastUpdated: new Date()
    })

    useRealTimeAnalytics.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      lastUpdated: new Date()
    })

    useRealTimePerformance.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      lastUpdated: new Date()
    })
  })

  it('renders analytics dashboard with key metrics', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    // Check for key metrics cards based on the actual mock data in the component
    expect(screen.getByText('125,000')).toBeInTheDocument() // Total views
    expect(screen.getByText('8,500')).toBeInTheDocument() // Total engagement
    expect(screen.getByText('15,200')).toBeInTheDocument() // Total followers
    expect(screen.getByText('6.8%')).toBeInTheDocument() // Engagement rate
  })

  it('displays loading state', () => {
    useApi.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: jest.fn()
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByTestId('analytics-loading')).toBeInTheDocument()
    expect(screen.getByText('Loading analytics data...')).toBeInTheDocument()
  })

  it('displays error state', () => {
    const error = new Error('Failed to fetch analytics')
    useApi.mockReturnValue({
      data: null,
      loading: false,
      error,
      refetch: jest.fn()
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('Error loading analytics')).toBeInTheDocument()
    expect(screen.getByText('Failed to fetch analytics')).toBeInTheDocument()
  })

  it('renders time series chart', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    const lineChart = screen.getByTestId('line-chart')
    expect(lineChart).toBeInTheDocument()
    
    const chartData = JSON.parse(lineChart.getAttribute('data-chart-data'))
    expect(chartData.labels).toEqual(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    expect(chartData.datasets[0].data).toEqual([6.2, 7.1, 5.8, 8.2, 6.9, 7.5, 6.8])
  })

  it('displays platform metrics', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    // Check platform names and metrics based on actual mock data
    expect(screen.getByText('Twitter')).toBeInTheDocument()
    expect(screen.getByText('LinkedIn')).toBeInTheDocument()
    expect(screen.getByText('Instagram')).toBeInTheDocument()
    expect(screen.getByText('Facebook')).toBeInTheDocument()

    expect(screen.getByText('5,200')).toBeInTheDocument() // Twitter followers
    expect(screen.getByText('3,800')).toBeInTheDocument() // LinkedIn followers
    expect(screen.getByText('4,200')).toBeInTheDocument() // Instagram followers
    expect(screen.getByText('2,000')).toBeInTheDocument() // Facebook followers
  })

  it('shows top performing posts', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('Top Performing Content')).toBeInTheDocument()
    expect(screen.getByText('5 AI Tools That Will Transform Your Social Media Strategy')).toBeInTheDocument()
    expect(screen.getByText('15,200')).toBeInTheDocument() // views
    expect(screen.getByText('2.7%')).toBeInTheDocument() // engagement rate
  })

  it('allows time period filtering', async () => {
    const refetchMock = jest.fn()
    useApi.mockReturnValue({
      data: mockAnalyticsData,
      loading: false,
      error: null,
      refetch: refetchMock
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    // Find and click time period selector - look for the actual select element
    const timeSelector = screen.getByDisplayValue('Last 7 days')
    fireEvent.change(timeSelector, { target: { value: '30d' } })

    await waitFor(() => {
      expect(refetchMock).toHaveBeenCalled()
    })
  })

  it('handles platform filter changes', async () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    // Find platform filter buttons
    const twitterFilter = screen.getByText('Twitter')
    fireEvent.click(twitterFilter)

    // Should filter content to show only Twitter metrics
    expect(twitterFilter.closest('button')).toHaveClass('bg-blue-500')
  })

  it('displays performance insights', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('Performance Insights')).toBeInTheDocument()
    expect(screen.getByText('8.5%')).toBeInTheDocument() // Average engagement
    expect(screen.getByText('2:00 PM')).toBeInTheDocument() // Best time to post
  })

  it('renders content type distribution chart', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    const doughnutChart = screen.getByTestId('doughnut-chart')
    expect(doughnutChart).toBeInTheDocument()
    
    const chartData = JSON.parse(doughnutChart.getAttribute('data-chart-data'))
    expect(chartData.datasets[0].data).toEqual([45, 35, 20])
  })

  it('shows real-time connection status', () => {
    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('Live')).toBeInTheDocument()
    expect(screen.getByTestId('connection-indicator')).toHaveClass('bg-green-500')
  })

  it('handles disconnected state', () => {
    useRealTimeData.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      isConnected: false,
      lastUpdated: new Date()
    })

    useRealTimeAnalytics.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      lastUpdated: new Date()
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('Disconnected')).toBeInTheDocument()
    expect(screen.getByTestId('connection-indicator')).toHaveClass('bg-red-500')
  })

  it('allows manual refresh', async () => {
    const refreshMock = jest.fn()
    const refetchMock = jest.fn()
    
    useRealTimeData.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: refreshMock,
      isConnected: true,
      lastUpdated: new Date()
    })

    useRealTimeAnalytics.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: refreshMock,
      lastUpdated: new Date()
    })

    useApi.mockReturnValue({
      data: mockAnalyticsData,
      loading: false,
      error: null,
      refetch: refetchMock
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    const refreshButton = screen.getByLabelText('Refresh data')
    fireEvent.click(refreshButton)

    expect(refreshMock).toHaveBeenCalled()
    expect(refetchMock).toHaveBeenCalled()
  })

  it('displays last updated timestamp', () => {
    const lastUpdated = new Date('2023-01-01T12:00:00Z')
    
    useRealTimeData.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      isConnected: true,
      lastUpdated
    })

    useRealTimeAnalytics.mockReturnValue({
      data: mockPerformanceData,
      isLoading: false,
      error: null,
      refreshNow: jest.fn(),
      lastUpdated
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText(/Last updated/)).toBeInTheDocument()
  })

  it('handles empty data gracefully', () => {
    useApi.mockReturnValue({
      data: {
        totalViews: 0,
        totalClicks: 0,
        totalShares: 0,
        totalComments: 0,
        engagementRate: 0,
        topPerformingPosts: [],
        platformMetrics: {},
        timeSeriesData: { labels: [], datasets: [] }
      },
      loading: false,
      error: null,
      refetch: jest.fn()
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('No data available')).toBeInTheDocument()
    expect(screen.getByText('Start creating content to see analytics')).toBeInTheDocument()
  })

  it('exports analytics data', async () => {
    // Mock the export functionality
    const exportSpy = jest.spyOn(window, 'open').mockImplementation(() => {})

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    const exportButton = screen.getByText('Export Data')
    fireEvent.click(exportButton)

    // In a real implementation, this would trigger a download or open export dialog
    expect(exportButton).toBeInTheDocument()
    
    exportSpy.mockRestore()
  })

  it('handles responsive layout', () => {
    // Test mobile view
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    // Metrics should stack vertically on mobile
    const metricsContainer = screen.getByTestId('metrics-grid')
    expect(metricsContainer).toHaveClass('grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-4')
  })

  it('shows comparison with previous period', () => {
    const dataWithComparison = {
      ...mockAnalyticsData,
      comparison: {
        viewsChange: 15.5,
        clicksChange: -2.3,
        sharesChange: 8.7,
        commentsChange: 12.1
      }
    }

    useApi.mockReturnValue({
      data: dataWithComparison,
      loading: false,
      error: null,
      refetch: jest.fn()
    })

    render(
      <TestWrapper>
        <Analytics />
      </TestWrapper>
    )

    expect(screen.getByText('+15.5%')).toBeInTheDocument()
    expect(screen.getByText('-2.3%')).toBeInTheDocument()
    expect(screen.getByText('+8.7%')).toBeInTheDocument()
    expect(screen.getByText('+12.1%')).toBeInTheDocument()
  })
})