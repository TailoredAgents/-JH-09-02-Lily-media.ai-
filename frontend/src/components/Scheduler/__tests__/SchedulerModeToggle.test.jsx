/**
 * PW-FE-REPLACE-001: Tests for SchedulerModeToggle component
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SchedulerModeToggle from '../SchedulerModeToggle'

describe('SchedulerModeToggle', () => {
  const defaultProps = {
    mode: 'content',
    onModeChange: vi.fn(),
  }

  beforeEach(() => {
    defaultProps.onModeChange.mockClear()
  })

  it('renders both mode buttons', () => {
    render(<SchedulerModeToggle {...defaultProps} />)

    expect(
      screen.getByRole('button', { name: /switch to content calendar mode/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /switch to service jobs mode/i })
    ).toBeInTheDocument()
  })

  it('highlights the active mode', () => {
    render(<SchedulerModeToggle {...defaultProps} mode="content" />)

    const contentButton = screen.getByRole('button', {
      name: /switch to content calendar mode/i,
    })
    const jobsButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })

    expect(contentButton).toHaveAttribute('aria-pressed', 'true')
    expect(jobsButton).toHaveAttribute('aria-pressed', 'false')

    // Check CSS classes for active state
    expect(contentButton).toHaveClass('bg-white', 'text-gray-900', 'shadow-sm')
    expect(jobsButton).toHaveClass('text-gray-600')
  })

  it('calls onModeChange when content button is clicked', () => {
    render(<SchedulerModeToggle {...defaultProps} mode="jobs" />)

    const contentButton = screen.getByRole('button', {
      name: /switch to content calendar mode/i,
    })
    fireEvent.click(contentButton)

    expect(defaultProps.onModeChange).toHaveBeenCalledWith('content')
  })

  it('calls onModeChange when jobs button is clicked', () => {
    render(<SchedulerModeToggle {...defaultProps} />)

    const jobsButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.click(jobsButton)

    expect(defaultProps.onModeChange).toHaveBeenCalledWith('jobs')
  })

  it('supports keyboard navigation with Enter key', () => {
    render(<SchedulerModeToggle {...defaultProps} />)

    const jobsButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.keyDown(jobsButton, { key: 'Enter' })

    expect(defaultProps.onModeChange).toHaveBeenCalledWith('jobs')
  })

  it('supports keyboard navigation with Space key', () => {
    render(<SchedulerModeToggle {...defaultProps} />)

    const jobsButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })
    fireEvent.keyDown(jobsButton, { key: ' ' })

    expect(defaultProps.onModeChange).toHaveBeenCalledWith('jobs')
  })

  it('applies custom className', () => {
    const customClass = 'custom-test-class'
    const { container } = render(
      <SchedulerModeToggle {...defaultProps} className={customClass} />
    )

    expect(container.firstChild).toHaveClass(customClass)
  })

  it('has proper ARIA attributes for accessibility', () => {
    render(<SchedulerModeToggle {...defaultProps} mode="content" />)

    const contentButton = screen.getByRole('button', {
      name: /switch to content calendar mode/i,
    })
    const jobsButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })

    expect(contentButton).toHaveAttribute('aria-pressed', 'true')
    expect(contentButton).toHaveAttribute(
      'aria-label',
      'Switch to Content Calendar mode'
    )

    expect(jobsButton).toHaveAttribute('aria-pressed', 'false')
    expect(jobsButton).toHaveAttribute(
      'aria-label',
      'Switch to Service Jobs mode'
    )
  })

  it('shows correct icons for each mode', () => {
    render(<SchedulerModeToggle {...defaultProps} />)

    // Check that icons are present (we can't easily test specific icons, but we can check structure)
    const contentButton = screen.getByRole('button', {
      name: /switch to content calendar mode/i,
    })
    const jobsButton = screen.getByRole('button', {
      name: /switch to service jobs mode/i,
    })

    expect(contentButton.querySelector('svg')).toBeInTheDocument()
    expect(jobsButton.querySelector('svg')).toBeInTheDocument()

    expect(screen.getByText('Content Calendar')).toBeInTheDocument()
    expect(screen.getByText('Service Jobs')).toBeInTheDocument()
  })
})
