/**
 * PW-FE-REPLACE-001: Integration tests for dual-mode Scheduler
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import Scheduler from '../Scheduler'

// Mock the API hook
vi.mock('../../hooks/useApi', () => ({
  useApi: () => ({
    apiService: {
      getContent: vi.fn().mockResolvedValue({ items: [] }),
      getJobs: vi.fn().mockResolvedValue({ jobs: [] }),
      checkJobWeather: vi
        .fn()
        .mockResolvedValue({ reschedule_recommended: false }),
      rescheduleJob: vi.fn().mockResolvedValue({}),
    },
    makeAuthenticatedRequest: vi.fn().mockImplementation((fn) => fn()),
  }),
}))

// Mock the real-time data hook
vi.mock('../../hooks/useRealTimeData', () => ({
  useRealTimeContent: () => ({
    data: null,
    isLoading: false,
  }),
}))

// Mock the drag and drop library
vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }) => <div data-testid="dnd-context">{children}</div>,
  DragOverlay: ({ children }) => <div>{children}</div>,
  useSensor: () => ({}),
  useSensors: () => [],
  PointerSensor: {},
  KeyboardSensor: {},
  closestCenter: () => ({}),
  pointerWithin: () => ({}),
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => {},
    transform: null,
    transition: null,
    isDragging: false,
  }),
  useDroppable: () => ({
    setNodeRef: () => {},
    isOver: false,
  }),
}))

vi.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Transform: {
      toString: () => '',
    },
  },
}))

// Mock date-fns to have predictable dates
vi.mock('date-fns', () => ({
  format: vi.fn((date, formatStr) => {
    if (formatStr === 'yyyy-MM-dd') return '2024-01-15'
    if (formatStr === 'MMM d') return 'Jan 15'
    if (formatStr === 'MMM d, yyyy') return 'Jan 15, 2024'
    if (formatStr === 'EEE') return 'Mon'
    if (formatStr === 'd') return '15'
    if (formatStr === 'h:mm a') return '10:00 AM'
    if (formatStr === 'HH:mm:ss') return '10:00:00'
    return 'Mocked Date'
  }),
  addDays: vi.fn(
    (date, days) => new Date(date.getTime() + days * 24 * 60 * 60 * 1000)
  ),
  startOfWeek: vi.fn((date) => date),
  endOfWeek: vi.fn((date) => date),
  isSameDay: vi.fn(() => false),
  parseISO: vi.fn((dateStr) => new Date(dateStr)),
}))

const renderSchedulerWithRouter = (props = {}) => {
  return render(
    <BrowserRouter>
      <Scheduler {...props} />
    </BrowserRouter>
  )
}

describe('Scheduler (Dual Mode)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders with content mode as default', () => {
    renderSchedulerWithRouter()

    // Should show the mode toggle
    expect(
      screen.getByRole('button', { name: /switch to content calendar mode/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /switch to service jobs mode/i })
    ).toBeInTheDocument()

    // Content mode should be active by default
    expect(
      screen.getByRole('button', { name: /switch to content calendar mode/i })
    ).toHaveAttribute('aria-pressed', 'true')

    // Should show content-specific elements
    expect(screen.getByText('Upcoming Posts')).toBeInTheDocument()
  })

  it('switches to jobs mode when toggle is clicked', async () => {
    renderSchedulerWithRouter()

    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      expect(screen.getByText('Upcoming Jobs')).toBeInTheDocument()
    })

    // Jobs mode should now be active
    expect(jobsModeButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows correct header text for each mode', async () => {
    renderSchedulerWithRouter()

    // Content mode header
    expect(
      screen.getByText(/Manage your content scheduler/)
    ).toBeInTheDocument()

    // Switch to jobs mode
    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      expect(
        screen.getByText(/Manage service job scheduling/)
      ).toBeInTheDocument()
    })
  })

  it('shows view mode toggle only in content mode', async () => {
    renderSchedulerWithRouter()

    // Should show view toggle in content mode
    expect(screen.getByRole('button', { name: /month/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /week/i })).toBeInTheDocument()

    // Switch to jobs mode
    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      // View toggle should not be visible in jobs mode
      expect(
        screen.queryByRole('button', { name: /month/i })
      ).not.toBeInTheDocument()
    })
  })

  it('renders navigation controls', () => {
    renderSchedulerWithRouter()

    // Previous/Next buttons
    const buttons = screen.getAllByRole('button')
    const navButtons = buttons.filter(
      (button) =>
        button.querySelector('svg') &&
        !button.textContent.includes('Content') &&
        !button.textContent.includes('Service') &&
        !button.textContent.includes('Month') &&
        !button.textContent.includes('Week')
    )

    expect(navButtons.length).toBeGreaterThan(0)

    // "This Week" button
    expect(
      screen.getByRole('button', { name: /this week/i })
    ).toBeInTheDocument()
  })

  it('loads content data on mount', () => {
    const { useApi } = require('../../hooks/useApi')
    const mockApi = useApi()

    renderSchedulerWithRouter()

    expect(mockApi.apiService.getContent).toHaveBeenCalled()
  })

  it('loads jobs data when switching to jobs mode', async () => {
    const { useApi } = require('../../hooks/useApi')
    const mockApi = useApi()

    renderSchedulerWithRouter()

    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      expect(mockApi.apiService.getJobs).toHaveBeenCalled()
    })
  })

  it('shows create post buttons only in content mode', async () => {
    renderSchedulerWithRouter()

    // Should show create post buttons in content mode
    expect(
      screen.getByRole('link', { name: /create new post/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /schedule from library/i })
    ).toBeInTheDocument()

    // Switch to jobs mode
    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      // Create post buttons should not be visible in jobs mode
      expect(
        screen.queryByRole('link', { name: /create new post/i })
      ).not.toBeInTheDocument()
      expect(
        screen.queryByRole('button', { name: /schedule from library/i })
      ).not.toBeInTheDocument()
    })
  })

  it('handles "This Week" navigation button click', () => {
    renderSchedulerWithRouter()

    const thisWeekButton = screen.getByRole('button', { name: /this week/i })
    fireEvent.click(thisWeekButton)

    // Should not crash and button should still be there
    expect(thisWeekButton).toBeInTheDocument()
  })

  it('handles navigation arrows', () => {
    renderSchedulerWithRouter()

    const buttons = screen.getAllByRole('button')
    const prevButton = buttons.find(
      (button) =>
        button.querySelector('svg') &&
        button.getAttribute('class')?.includes('border-gray-300')
    )

    if (prevButton) {
      fireEvent.click(prevButton)
      // Should not crash
      expect(
        screen.getByText(/Manage your content scheduler/)
      ).toBeInTheDocument()
    }
  })

  it('preserves content mode state when switching views', async () => {
    renderSchedulerWithRouter()

    // Switch to month view
    const monthButton = screen.getByRole('button', { name: /month/i })
    fireEvent.click(monthButton)

    // Switch to jobs mode and back
    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      expect(screen.getByText('Upcoming Jobs')).toBeInTheDocument()
    })

    const contentModeButton = screen.getByRole('button', {
      name: /switch to content calendar mode/i,
    })
    fireEvent.click(contentModeButton)

    await waitFor(() => {
      // Should return to content mode and still show month view option
      expect(screen.getByRole('button', { name: /month/i })).toBeInTheDocument()
      expect(screen.getByText('Upcoming Posts')).toBeInTheDocument()
    })
  })

  it('has proper accessibility attributes', () => {
    renderSchedulerWithRouter()

    // Mode toggle buttons should have proper ARIA attributes
    expect(
      screen.getByRole('button', { name: /switch to content calendar mode/i })
    ).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('button', { name: /switch to service jobs mode/i })
    ).toHaveAttribute('aria-pressed', 'false')
  })

  it('handles keyboard navigation on mode toggle', () => {
    renderSchedulerWithRouter()

    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })

    // Test Enter key
    fireEvent.keyDown(jobsModeButton, { key: 'Enter' })
    expect(jobsModeButton).toHaveAttribute('aria-pressed', 'true')

    const contentModeButton = screen.getByRole('button', {
      name: /switch to content calendar mode/i,
    })

    // Test Space key
    fireEvent.keyDown(contentModeButton, { key: ' ' })
    expect(contentModeButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('displays empty state messages appropriately', async () => {
    renderSchedulerWithRouter()

    // Content mode empty state
    await waitFor(() => {
      expect(
        screen.getByText('No upcoming posts scheduled')
      ).toBeInTheDocument()
    })

    // Switch to jobs mode
    const jobsModeButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsModeButton)

    await waitFor(() => {
      expect(screen.getByText('No upcoming jobs scheduled')).toBeInTheDocument()
    })
  })
})
