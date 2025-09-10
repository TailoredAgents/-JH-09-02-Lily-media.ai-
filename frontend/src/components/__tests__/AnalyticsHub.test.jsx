import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import AnalyticsHub from '../AnalyticsHub'
import apiService from '../../services/api'

// Mock the API service
jest.mock('../../services/api')

// Mock Chart.js components to avoid canvas rendering issues in tests
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>,
  Bar: () => <div data-testid="bar-chart">Bar Chart</div>,
  Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>,
}))

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
}))

describe('AnalyticsHub', () => {
  const mockAnalyticsData = {
    totals: {
      leads: 150,
      quotes: 85,
      quotes_accepted: 42,
      jobs_scheduled: 38,
      jobs_completed: 35,
      revenue: 87500.0,
      avg_ticket: 2500.0,
      acceptance_rate: 0.494,
      completion_rate: 0.921,
      lead_to_quote_rate: 0.567,
      quote_to_job_rate: 0.905,
    },
    time_series: [
      {
        period: '2025-01-15',
        leads: 5,
        quotes: 3,
        quotes_accepted: 2,
        jobs_scheduled: 2,
        jobs_completed: 1,
        revenue: 2500.0,
      },
    ],
    platform_breakdown: [
      {
        platform: 'facebook',
        leads: 80,
        quotes: 45,
        quotes_accepted: 22,
        jobs_completed: 20,
        revenue: 50000.0,
      },
    ],
    service_type_breakdown: [
      {
        service_type: 'pressure_washing',
        jobs_scheduled: 25,
        jobs_completed: 23,
        revenue: 57500.0,
        avg_ticket: 2500.0,
      },
    ],
  }

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it('renders loading state initially', () => {
    apiService.getBusinessAnalytics = jest.fn(() => new Promise(() => {})) // Never resolves

    render(<AnalyticsHub darkMode={false} />)

    expect(screen.getByText('Loading analytics...')).toBeInTheDocument()
  })

  it('renders business KPIs from mocked API data', async () => {
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockResolvedValue(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('Total Leads')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument()
      expect(screen.getByText('Quotes Sent')).toBeInTheDocument()
      expect(screen.getByText('85')).toBeInTheDocument()
      expect(screen.getByText('Total Revenue')).toBeInTheDocument()
      expect(screen.getByText('$87,500')).toBeInTheDocument()
      expect(screen.getByText('Acceptance Rate')).toBeInTheDocument()
      expect(screen.getByText('49.4%')).toBeInTheDocument()
    })
  })

  it('shows empty state when no data available', async () => {
    const emptyData = {
      totals: {
        leads: 0,
        quotes: 0,
        quotes_accepted: 0,
        jobs_scheduled: 0,
        jobs_completed: 0,
        revenue: 0,
        avg_ticket: 0,
        acceptance_rate: 0,
        completion_rate: 0,
        lead_to_quote_rate: 0,
        quote_to_job_rate: 0,
      },
      time_series: [],
      platform_breakdown: [],
      service_type_breakdown: [],
    }

    apiService.getBusinessAnalytics = jest.fn().mockResolvedValue(emptyData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('No business data yet')).toBeInTheDocument()
      expect(
        screen.getByText(
          'Start generating leads and quotes to see your business metrics here.'
        )
      ).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    const errorMessage = 'Failed to fetch analytics'
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockRejectedValue(new Error(errorMessage))

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('Unable to load analytics')).toBeInTheDocument()
      expect(screen.getByText('Try Again')).toBeInTheDocument()
    })
  })

  it('filter changes refetch and update data', async () => {
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockResolvedValue(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('Total Leads')).toBeInTheDocument()
    })

    // Change platform filter
    const platformSelect = screen.getByDisplayValue('All Platforms')
    fireEvent.change(platformSelect, { target: { value: 'facebook' } })

    await waitFor(() => {
      expect(apiService.getBusinessAnalytics).toHaveBeenCalledWith(
        expect.objectContaining({
          platform: 'facebook',
        })
      )
    })
  })

  it('group by filter changes update API calls', async () => {
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockResolvedValue(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('Total Leads')).toBeInTheDocument()
    })

    // Change group by filter
    const groupBySelect = screen.getByDisplayValue('Daily')
    fireEvent.change(groupBySelect, { target: { value: 'week' } })

    await waitFor(() => {
      expect(apiService.getBusinessAnalytics).toHaveBeenCalledWith(
        expect.objectContaining({
          group_by: 'week',
        })
      )
    })
  })

  it('renders charts when data is available', async () => {
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockResolvedValue(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
      expect(screen.getByTestId('doughnut-chart')).toBeInTheDocument()
      expect(screen.getAllByTestId('bar-chart')).toHaveLength(2) // Conversion funnel + service type
    })
  })

  it('has proper accessibility attributes', async () => {
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockResolvedValue(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      // Check for proper heading structure
      expect(
        screen.getByRole('heading', { level: 1, name: 'Business Analytics' })
      ).toBeInTheDocument()

      // Check for proper form labels
      expect(screen.getByLabelText('Platform')).toBeInTheDocument()
      expect(screen.getByLabelText('Time Period')).toBeInTheDocument()
      expect(screen.getByLabelText('Group By')).toBeInTheDocument()

      // Check for metric cards have proper titles (tooltips)
      const leadsCard = screen.getByText('Total Leads').closest('div')
      expect(leadsCard).toHaveAttribute(
        'title',
        'Leads generated from social media'
      )
    })
  })

  it('retry button works after error', async () => {
    const errorMessage = 'Network error'
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockRejectedValueOnce(new Error(errorMessage))
      .mockResolvedValueOnce(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('Unable to load analytics')).toBeInTheDocument()
    })

    // Click retry button
    const retryButton = screen.getByText('Try Again')
    fireEvent.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('Total Leads')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument()
    })

    expect(apiService.getBusinessAnalytics).toHaveBeenCalledTimes(2)
  })

  it('displays social metrics as secondary information', async () => {
    apiService.getBusinessAnalytics = jest
      .fn()
      .mockResolvedValue(mockAnalyticsData)

    render(<AnalyticsHub darkMode={false} />)

    await waitFor(() => {
      expect(screen.getByText('Social Media Metrics')).toBeInTheDocument()
      expect(screen.getByText('Total Reach')).toBeInTheDocument()
      expect(screen.getByText('45.2K')).toBeInTheDocument()
      expect(screen.getByText('Engagement Rate')).toBeInTheDocument()
      expect(screen.getByText('4.8%')).toBeInTheDocument()
    })
  })
})
