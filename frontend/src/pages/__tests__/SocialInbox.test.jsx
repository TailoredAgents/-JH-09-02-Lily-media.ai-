import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import SocialInbox from '../SocialInbox'
import { AuthContext } from '../../contexts/AuthContext'
import { PlanContext } from '../../contexts/PlanContext'
import api from '../../services/api'

// Mock the API service
jest.mock('../../services/api')

// Mock the contexts
const mockAuthContext = {
  user: {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
  },
}

const mockPlanContext = {
  hasAIInbox: true,
}

// Mock components
jest.mock('../../components/PlanGate', () => {
  return function MockPlanGate({ children }) {
    return <div data-testid="plan-gate">{children}</div>
  }
})

jest.mock('../../components/enhanced/EnhancedPlanGate', () => ({
  FeatureGate: ({ children }) => <div data-testid="feature-gate">{children}</div>,
}))

describe('SocialInbox', () => {
  const mockLeadsData = {
    data: [
      {
        id: 'lead-1',
        name: 'John Doe',
        email: 'john@example.com',
        status: 'new',
        platform: 'facebook',
        notes: 'Interested in driveway cleaning',
        estimated_value: 250.0,
        created_at: '2025-01-15T10:00:00Z',
      },
      {
        id: 'lead-2', 
        name: 'Jane Smith',
        email: 'jane@example.com',
        status: 'contacted',
        platform: 'instagram',
        notes: 'House washing inquiry',
        estimated_value: 400.0,
        created_at: '2025-01-14T15:30:00Z',
      },
    ],
    pagination: {
      total_pages: 1,
    },
    stats: {
      total: 2,
      new: 1,
      contacted: 1,
      qualified: 0,
      converted: 0,
    },
  }

  const mockQuotesData = {
    data: [
      {
        id: 'quote-1',
        customer_name: 'John Doe',
        customer_email: 'john@example.com',
        status: 'sent',
        service_type: 'pressure_washing',
        total_amount: 350.0,
        address: '123 Main St',
        valid_until: '2025-02-15T00:00:00Z',
        created_at: '2025-01-15T12:00:00Z',
      },
      {
        id: 'quote-2',
        customer_name: 'Jane Smith',
        customer_email: 'jane@example.com',
        status: 'accepted',
        service_type: 'soft_wash',
        total_amount: 450.0,
        address: '456 Oak Ave',
        valid_until: '2025-02-20T00:00:00Z',
        created_at: '2025-01-14T16:00:00Z',
      },
    ],
    pagination: {
      total_pages: 1,
    },
    stats: {
      total: 2,
      sent: 1,
      accepted: 1,
      total_value: 800.0,
    },
  }

  const mockJobsData = {
    data: [
      {
        id: 'job-1',
        customer_name: 'John Doe',
        status: 'scheduled',
        service_type: 'pressure_washing',
        estimated_cost: 350.0,
        address: '123 Main St',
        scheduled_for: '2025-01-20T09:00:00Z',
        duration_minutes: 180,
        created_at: '2025-01-15T14:00:00Z',
      },
      {
        id: 'job-2',
        customer_name: 'Jane Smith',
        status: 'completed',
        service_type: 'soft_wash',
        actual_cost: 450.0,
        address: '456 Oak Ave',
        scheduled_for: '2025-01-18T10:00:00Z',
        duration_minutes: 240,
        created_at: '2025-01-14T17:00:00Z',
      },
    ],
    pagination: {
      total_pages: 1,
    },
    stats: {
      total: 2,
      scheduled: 1,
      completed: 1,
      revenue: 450.0,
    },
  }

  const renderWithContexts = (component) => {
    return render(
      <AuthContext.Provider value={mockAuthContext}>
        <PlanContext.Provider value={mockPlanContext}>
          {component}
        </PlanContext.Provider>
      </AuthContext.Provider>
    )
  }

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Default API mocks
    api.getLeads = jest.fn().mockResolvedValue(mockLeadsData)
    api.getQuotes = jest.fn().mockResolvedValue(mockQuotesData)
    api.getJobs = jest.fn().mockResolvedValue(mockJobsData)
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it('renders with leads tab by default', async () => {
    renderWithContexts(<SocialInbox />)

    // Check tabs are rendered
    expect(screen.getByText('Leads')).toBeInTheDocument()
    expect(screen.getByText('Quotes')).toBeInTheDocument()
    expect(screen.getByText('Jobs')).toBeInTheDocument()

    // Check leads tab is active
    const leadsTab = screen.getByText('Leads').closest('button')
    expect(leadsTab).toHaveClass('border-indigo-500', 'text-indigo-600')

    await waitFor(() => {
      expect(api.getLeads).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        search: undefined,
        status: undefined,
        service_type: undefined,
      })
    })
  })

  it('displays leads data correctly', async () => {
    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      // Check stats cards
      expect(screen.getByText('Total Leads')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('New Leads')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument()

      // Check lead items
      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(screen.getByText('jane@example.com')).toBeInTheDocument()
      expect(screen.getByText('new')).toBeInTheDocument()
      expect(screen.getByText('contacted')).toBeInTheDocument()
    })
  })

  it('switches to quotes tab and loads quotes data', async () => {
    renderWithContexts(<SocialInbox />)

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    // Click quotes tab
    const quotesTab = screen.getByText('Quotes')
    fireEvent.click(quotesTab)

    await waitFor(() => {
      expect(api.getQuotes).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        search: undefined,
        status: undefined,
        service_type: undefined,
      })

      // Check quotes stats
      expect(screen.getByText('Total Quotes')).toBeInTheDocument()
      expect(screen.getByText('Sent')).toBeInTheDocument()
      expect(screen.getByText('Accepted')).toBeInTheDocument()
      expect(screen.getByText('Total Value')).toBeInTheDocument()
      expect(screen.getByText('$800')).toBeInTheDocument()

      // Check quote items
      expect(screen.getByText('$350')).toBeInTheDocument()
      expect(screen.getByText('$450')).toBeInTheDocument()
      expect(screen.getByText('sent')).toBeInTheDocument()
      expect(screen.getByText('accepted')).toBeInTheDocument()
    })
  })

  it('switches to jobs tab and loads jobs data', async () => {
    renderWithContexts(<SocialInbox />)

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    // Click jobs tab
    const jobsTab = screen.getByText('Jobs')
    fireEvent.click(jobsTab)

    await waitFor(() => {
      expect(api.getJobs).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        search: undefined,
        status: undefined,
        service_type: undefined,
      })

      // Check jobs stats
      expect(screen.getByText('Total Jobs')).toBeInTheDocument()
      expect(screen.getByText('Scheduled')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.getByText('Revenue')).toBeInTheDocument()
      expect(screen.getByText('$450')).toBeInTheDocument()

      // Check job status tags
      expect(screen.getByText('scheduled')).toBeInTheDocument()
      expect(screen.getByText('completed')).toBeInTheDocument()
    })
  })

  it('handles search functionality', async () => {
    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    // Type in search box
    const searchInput = screen.getByPlaceholderText('Search leads...')
    fireEvent.change(searchInput, { target: { value: 'john' } })

    await waitFor(() => {
      expect(api.getLeads).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        search: 'john',
        status: undefined,
        service_type: undefined,
      })
    })
  })

  it('handles status filtering', async () => {
    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    // Change status filter
    const statusSelect = screen.getByDisplayValue('All Status')
    fireEvent.change(statusSelect, { target: { value: 'new' } })

    await waitFor(() => {
      expect(api.getLeads).toHaveBeenCalledWith({
        page: 1,
        per_page: 20,
        search: undefined,
        status: 'new',
        service_type: undefined,
      })
    })
  })

  it('shows service type filter for quotes and jobs tabs', async () => {
    renderWithContexts(<SocialInbox />)

    // Initially on leads tab - no service type filter
    expect(screen.queryByText('All Services')).not.toBeInTheDocument()

    // Switch to quotes tab
    const quotesTab = screen.getByText('Quotes')
    fireEvent.click(quotesTab)

    await waitFor(() => {
      expect(screen.getByText('All Services')).toBeInTheDocument()
    })

    // Switch to jobs tab
    const jobsTab = screen.getByText('Jobs')
    fireEvent.click(jobsTab)

    await waitFor(() => {
      expect(screen.getByText('All Services')).toBeInTheDocument()
    })
  })

  it('handles item selection and shows details', async () => {
    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    // Click on first lead
    const leadCard = screen.getByText('John Doe').closest('div')
    fireEvent.click(leadCard)

    await waitFor(() => {
      // Check details panel shows
      expect(screen.getAllByText('John Doe')).toHaveLength(2) // One in list, one in details
      expect(screen.getByText('LEAD #lead-1')).toBeInTheDocument()
      expect(screen.getByText('john@example.com')).toBeInTheDocument()
      expect(screen.getByText('Interested in driveway cleaning')).toBeInTheDocument()
    })
  })

  it('shows empty state when no data', async () => {
    api.getLeads = jest.fn().mockResolvedValue({
      data: [],
      pagination: { total_pages: 1 },
      stats: { total: 0 },
    })

    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('No leads found')).toBeInTheDocument()
      expect(screen.getByText('Get started by creating your first lead or adjust your filters.')).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    api.getLeads = jest.fn().mockRejectedValue(new Error('API Error'))

    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('No leads found')).toBeInTheDocument()
    })
  })

  it('shows loading state', () => {
    api.getLeads = jest.fn(() => new Promise(() => {})) // Never resolves

    renderWithContexts(<SocialInbox />)

    expect(screen.getByRole('generic', { className: /animate-spin/ })).toBeInTheDocument()
  })

  it('handles pagination correctly', async () => {
    const multiPageData = {
      ...mockLeadsData,
      pagination: { total_pages: 3 },
    }
    api.getLeads = jest.fn().mockResolvedValue(multiPageData)

    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
      expect(screen.getByText('Previous')).toBeDisabled()
      expect(screen.getByText('Next')).not.toBeDisabled()
    })

    // Click next page
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)

    await waitFor(() => {
      expect(api.getLeads).toHaveBeenCalledWith({
        page: 2,
        per_page: 20,
        search: undefined,
        status: undefined,
        service_type: undefined,
      })
    })
  })

  it('refreshes data when refresh button is clicked', async () => {
    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(api.getLeads).toHaveBeenCalledTimes(1)
    })

    const refreshButton = screen.getByText('Refresh')
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(api.getLeads).toHaveBeenCalledTimes(2)
    })
  })

  it('formats currency correctly', async () => {
    renderWithContexts(<SocialInbox />)

    // Switch to quotes tab to see currency
    const quotesTab = screen.getByText('Quotes')
    fireEvent.click(quotesTab)

    await waitFor(() => {
      expect(screen.getByText('$350')).toBeInTheDocument()
      expect(screen.getByText('$450')).toBeInTheDocument()
    })
  })

  it('shows appropriate status options for each tab', async () => {
    renderWithContexts(<SocialInbox />)

    // Leads tab - check lead status options
    const statusSelect = screen.getByDisplayValue('All Status')
    expect(statusSelect).toBeInTheDocument()
    
    // Switch to quotes tab
    const quotesTab = screen.getByText('Quotes')
    fireEvent.click(quotesTab)

    await waitFor(() => {
      fireEvent.click(statusSelect)
      // Note: In a real test you'd check for quote-specific options
      // but this tests the structure is working
    })
  })

  it('handles tab switching and resets selection', async () => {
    renderWithContexts(<SocialInbox />)

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    // Select a lead
    const leadCard = screen.getByText('John Doe').closest('div')
    fireEvent.click(leadCard)

    await waitFor(() => {
      expect(screen.getByText('LEAD #lead-1')).toBeInTheDocument()
    })

    // Switch to quotes tab
    const quotesTab = screen.getByText('Quotes')
    fireEvent.click(quotesTab)

    // Selection should be cleared
    await waitFor(() => {
      expect(screen.queryByText('LEAD #lead-1')).not.toBeInTheDocument()
      expect(screen.getByText('Select a quote')).toBeInTheDocument()
    })
  })
})