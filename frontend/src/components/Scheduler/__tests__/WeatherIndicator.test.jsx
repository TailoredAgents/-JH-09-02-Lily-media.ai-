/**
 * PW-FE-REPLACE-001: Tests for WeatherIndicator component
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import WeatherIndicator from '../WeatherIndicator'

describe('WeatherIndicator', () => {
  const defaultProps = {
    jobId: 'job-123',
    isRisky: true,
    onClick: vi.fn(),
  }

  beforeEach(() => {
    defaultProps.onClick.mockClear()
  })

  it('renders nothing when isRisky is false', () => {
    const { container } = render(
      <WeatherIndicator {...defaultProps} isRisky={false} />
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders weather warning button when isRisky is true', () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
    expect(button).toHaveAttribute(
      'aria-label',
      'Weather warning for job job-123. Click for details.'
    )
  })

  it('shows tooltip on hover', async () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    fireEvent.mouseEnter(button)

    await waitFor(() => {
      expect(screen.getByText('Weather Risk Detected')).toBeInTheDocument()
      expect(
        screen.getByText('Click for detailed forecast')
      ).toBeInTheDocument()
    })
  })

  it('hides tooltip on mouse leave', async () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    fireEvent.mouseEnter(button)

    await waitFor(() => {
      expect(screen.getByText('Weather Risk Detected')).toBeInTheDocument()
    })

    fireEvent.mouseLeave(button)

    await waitFor(() => {
      expect(
        screen.queryByText('Weather Risk Detected')
      ).not.toBeInTheDocument()
    })
  })

  it('shows tooltip on focus and hides on blur', async () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    fireEvent.focus(button)

    await waitFor(() => {
      expect(screen.getByText('Weather Risk Detected')).toBeInTheDocument()
    })

    fireEvent.blur(button)

    await waitFor(() => {
      expect(
        screen.queryByText('Weather Risk Detected')
      ).not.toBeInTheDocument()
    })
  })

  it('displays custom reasons in tooltip', async () => {
    const reasons = [
      'High rain probability: 80%',
      'Strong winds: 25 mph',
      'Low temperature: 30°F',
    ]

    render(<WeatherIndicator {...defaultProps} reasons={reasons} />)

    const button = screen.getByRole('button')
    fireEvent.mouseEnter(button)

    await waitFor(() => {
      expect(
        screen.getByText('• High rain probability: 80%')
      ).toBeInTheDocument()
      expect(screen.getByText('• Strong winds: 25 mph')).toBeInTheDocument()
      expect(screen.getByText('• Low temperature: 30°F')).toBeInTheDocument()
    })
  })

  it('truncates reasons list and shows count when more than 3', async () => {
    const reasons = ['Reason 1', 'Reason 2', 'Reason 3', 'Reason 4', 'Reason 5']

    render(<WeatherIndicator {...defaultProps} reasons={reasons} />)

    const button = screen.getByRole('button')
    fireEvent.mouseEnter(button)

    await waitFor(() => {
      expect(screen.getByText('• Reason 1')).toBeInTheDocument()
      expect(screen.getByText('• Reason 2')).toBeInTheDocument()
      expect(screen.getByText('• Reason 3')).toBeInTheDocument()
      expect(screen.getByText('+2 more reasons')).toBeInTheDocument()
      expect(screen.queryByText('• Reason 4')).not.toBeInTheDocument()
    })
  })

  it('calls onClick when button is clicked', () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(defaultProps.onClick).toHaveBeenCalledWith('job-123')
  })

  it('calls onClick when Enter key is pressed', () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    fireEvent.keyDown(button, { key: 'Enter' })

    expect(defaultProps.onClick).toHaveBeenCalledWith('job-123')
  })

  it('calls onClick when Space key is pressed', () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    fireEvent.keyDown(button, { key: ' ' })

    expect(defaultProps.onClick).toHaveBeenCalledWith('job-123')
  })

  it('stops event propagation when clicked', () => {
    const parentClickHandler = vi.fn()

    render(
      <div onClick={parentClickHandler}>
        <WeatherIndicator {...defaultProps} />
      </div>
    )

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(defaultProps.onClick).toHaveBeenCalledWith('job-123')
    expect(parentClickHandler).not.toHaveBeenCalled()
  })

  it('applies different colors based on severity', () => {
    const { rerender } = render(
      <WeatherIndicator {...defaultProps} severity="severe" />
    )

    let button = screen.getByRole('button')
    expect(button).toHaveClass('bg-red-500')

    rerender(<WeatherIndicator {...defaultProps} severity="moderate" />)
    button = screen.getByRole('button')
    expect(button).toHaveClass('bg-amber-500')

    rerender(<WeatherIndicator {...defaultProps} severity="light" />)
    button = screen.getByRole('button')
    expect(button).toHaveClass('bg-yellow-500')
  })

  it('applies pulse animation for severe weather', () => {
    render(<WeatherIndicator {...defaultProps} severity="severe" />)

    const button = screen.getByRole('button')
    expect(button).toHaveClass('animate-pulse')
  })

  it('applies custom className', () => {
    const { container } = render(
      <WeatherIndicator {...defaultProps} className="custom-test-class" />
    )

    expect(container.firstChild).toHaveClass('custom-test-class')
  })

  it('has proper accessibility attributes', () => {
    render(<WeatherIndicator {...defaultProps} />)

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('type', 'button')
    expect(button).toHaveAttribute(
      'title',
      'Weather conditions may affect this job'
    )
    expect(button).toHaveAttribute(
      'aria-label',
      'Weather warning for job job-123. Click for details.'
    )
  })
})
