import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import Settings from '../Settings'
import { AuthContext } from '../../contexts/AuthContext'
import { PlanContext } from '../../contexts/PlanContext'
import api from '../../services/api'

// Mock the API service
jest.mock('../../services/api')

const mockAuthContext = {
  user: {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
  },
}

const mockPlanContext = {
  plan: {
    tier: 'pro',
    features: ['pricing', 'weather', 'booking'],
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

describe('Settings', () => {
  const mockPricingSettings = {
    base_rates: {
      house_washing: 0.15,
      pressure_washing: 0.12,
      soft_wash: 0.18,
      deck_cleaning: 0.20,
      concrete_cleaning: 0.10,
      gutter_cleaning: 0.08,
    },
    min_job_total: 150.0,
    bundles: [
      {
        name: 'House + Driveway',
        services: ['house_washing', 'concrete_cleaning'],
        discount_percent: 15,
      },
    ],
    seasonal_modifiers: [
      {
        season: 'spring',
        multiplier: 1.1,
        description: 'High demand season',
      },
    ],
  }

  const mockWeatherSettings = {
    rain_probability_threshold: 30,
    wind_speed_threshold: 25,
    temperature_threshold: 40,
    lookahead_days: 3,
    auto_reschedule: true,
    notification_hours_ahead: 24,
  }

  const mockBookingSettings = {
    intent_threshold: 0.75,
    require_photos: true,
    required_fields: ['customer_name', 'phone', 'address', 'service_type'],
    auto_followup_hours: 24,
    quiet_hours: {
      enabled: true,
      start: '20:00',
      end: '08:00',
    },
    business_hours: {
      monday: { enabled: true, start: '08:00', end: '18:00' },
      tuesday: { enabled: true, start: '08:00', end: '18:00' },
      wednesday: { enabled: true, start: '08:00', end: '18:00' },
      thursday: { enabled: true, start: '08:00', end: '18:00' },
      friday: { enabled: true, start: '08:00', end: '18:00' },
      saturday: { enabled: true, start: '09:00', end: '17:00' },
      sunday: { enabled: false, start: '10:00', end: '16:00' },
    },
    buffer_minutes: 30,
  }

  beforeEach(() => {
    jest.clearAllMocks()

    // Default API mocks
    api.getPricingSettings = jest.fn().mockResolvedValue(mockPricingSettings)
    api.getWeatherSettings = jest.fn().mockResolvedValue(mockWeatherSettings)
    api.getBookingSettings = jest.fn().mockResolvedValue(mockBookingSettings)
    api.updatePricingSettings = jest.fn().mockResolvedValue({ success: true })
    api.updateWeatherSettings = jest.fn().mockResolvedValue({ success: true })
    api.updateBookingSettings = jest.fn().mockResolvedValue({ success: true })
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  it('renders with pricing tab active by default', async () => {
    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Business Settings')).toBeInTheDocument()
    })

    // Check that pricing tab is active
    const pricingTab = screen.getByText('Pricing').closest('button')
    expect(pricingTab).toHaveClass('bg-indigo-50', 'text-indigo-700')

    // Check that pricing content is visible
    expect(screen.getByText('Base Rates (per sq ft)')).toBeInTheDocument()
    expect(screen.getByText('Minimum Job Total')).toBeInTheDocument()
  })

  it('loads settings on component mount', async () => {
    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(api.getPricingSettings).toHaveBeenCalled()
      expect(api.getWeatherSettings).toHaveBeenCalled()
      expect(api.getBookingSettings).toHaveBeenCalled()
    })
  })

  it('switches between tabs correctly', async () => {
    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Base Rates (per sq ft)')).toBeInTheDocument()
    })

    // Switch to weather tab
    const weatherTab = screen.getByText('Weather')
    fireEvent.click(weatherTab)

    await waitFor(() => {
      expect(screen.getByText('Weather Thresholds')).toBeInTheDocument()
      expect(screen.getByText('Rain Probability Threshold')).toBeInTheDocument()
    })

    // Switch to booking tab
    const bookingTab = screen.getByText('Booking Policies')
    fireEvent.click(bookingTab)

    await waitFor(() => {
      expect(screen.getByText('Lead Qualification')).toBeInTheDocument()
      expect(screen.getByText('Intent Confidence Threshold')).toBeInTheDocument()
    })
  })

  it('displays and allows editing pricing settings', async () => {
    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('0.15')).toBeInTheDocument() // house_washing rate
      expect(screen.getByDisplayValue('150')).toBeInTheDocument() // min_job_total
    })

    // Edit house washing rate
    const houseWashingInput = screen.getByDisplayValue('0.15')
    fireEvent.change(houseWashingInput, { target: { value: '0.20' } })

    expect(screen.getByDisplayValue('0.20')).toBeInTheDocument()

    // Edit minimum job total
    const minJobTotalInput = screen.getByDisplayValue('150')
    fireEvent.change(minJobTotalInput, { target: { value: '200' } })

    expect(screen.getByDisplayValue('200')).toBeInTheDocument()
  })

  it('displays and allows editing weather settings', async () => {
    renderWithContexts(<Settings />)

    // Switch to weather tab
    const weatherTab = screen.getByText('Weather')
    fireEvent.click(weatherTab)

    await waitFor(() => {
      expect(screen.getByText('30%')).toBeInTheDocument() // rain threshold
      expect(screen.getByText('25 mph')).toBeInTheDocument() // wind threshold
    })

    // Change rain probability threshold
    const rainSlider = screen.getByDisplayValue('30')
    fireEvent.change(rainSlider, { target: { value: '40' } })

    await waitFor(() => {
      expect(screen.getByText('40%')).toBeInTheDocument()
    })
  })

  it('displays and allows editing booking settings', async () => {
    renderWithContexts(<Settings />)

    // Switch to booking tab
    const bookingTab = screen.getByText('Booking Policies')
    fireEvent.click(bookingTab)

    await waitFor(() => {
      expect(screen.getByText('75%')).toBeInTheDocument() // intent threshold
    })

    // Check required fields checkboxes
    const customerNameCheckbox = screen.getByLabelText('Customer Name')
    const phoneCheckbox = screen.getByLabelText('Phone')

    expect(customerNameCheckbox).toBeChecked()
    expect(phoneCheckbox).toBeChecked()

    // Toggle photo requirement
    const requirePhotosToggle = screen.getByText('Require Photos').closest('div').querySelector('button')
    fireEvent.click(requirePhotosToggle)

    // Check business hours
    const mondayCheckbox = screen.getByLabelText('Monday')
    expect(mondayCheckbox).toBeChecked()

    const sundayCheckbox = screen.getByLabelText('Sunday')
    expect(sundayCheckbox).not.toBeChecked()
  })

  it('saves pricing settings when save button is clicked', async () => {
    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Base Rates (per sq ft)')).toBeInTheDocument()
    })

    // Edit a setting
    const houseWashingInput = screen.getByDisplayValue('0.15')
    fireEvent.change(houseWashingInput, { target: { value: '0.20' } })

    // Click save
    const saveButton = screen.getByText('Save Pricing Settings')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(api.updatePricingSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          base_rates: expect.objectContaining({
            house_washing: 0.20,
          }),
        })
      )
    })

    // Check success message
    await waitFor(() => {
      expect(screen.getByText('pricing settings saved successfully!')).toBeInTheDocument()
    })
  })

  it('saves weather settings when save button is clicked', async () => {
    renderWithContexts(<Settings />)

    // Switch to weather tab
    const weatherTab = screen.getByText('Weather')
    fireEvent.click(weatherTab)

    await waitFor(() => {
      expect(screen.getByText('Weather Thresholds')).toBeInTheDocument()
    })

    // Edit rain threshold
    const rainSlider = screen.getByDisplayValue('30')
    fireEvent.change(rainSlider, { target: { value: '40' } })

    // Click save
    const saveButton = screen.getByText('Save Weather Settings')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(api.updateWeatherSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          rain_probability_threshold: 40,
        })
      )
    })

    // Check success message
    await waitFor(() => {
      expect(screen.getByText('weather settings saved successfully!')).toBeInTheDocument()
    })
  })

  it('saves booking settings when save button is clicked', async () => {
    renderWithContexts(<Settings />)

    // Switch to booking tab
    const bookingTab = screen.getByText('Booking Policies')
    fireEvent.click(bookingTab)

    await waitFor(() => {
      expect(screen.getByText('Lead Qualification')).toBeInTheDocument()
    })

    // Toggle require photos
    const requirePhotosToggle = screen.getByText('Require Photos').closest('div').querySelector('button')
    fireEvent.click(requirePhotosToggle)

    // Click save
    const saveButton = screen.getByText('Save Booking Settings')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(api.updateBookingSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          require_photos: false,
        })
      )
    })

    // Check success message
    await waitFor(() => {
      expect(screen.getByText('booking settings saved successfully!')).toBeInTheDocument()
    })
  })

  it('displays error messages when API calls fail', async () => {
    api.updatePricingSettings = jest.fn().mockRejectedValue(new Error('Save failed'))

    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Base Rates (per sq ft)')).toBeInTheDocument()
    })

    // Click save to trigger error
    const saveButton = screen.getByText('Save Pricing Settings')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Save failed')).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    api.getPricingSettings = jest.fn(() => new Promise(() => {})) // Never resolves

    renderWithContexts(<Settings />)

    expect(screen.getByRole('generic', { className: /animate-spin/ })).toBeInTheDocument()
  })

  it('handles settings load failure gracefully', async () => {
    api.getPricingSettings = jest.fn().mockRejectedValue(new Error('Load failed'))
    api.getWeatherSettings = jest.fn().mockRejectedValue(new Error('Load failed'))
    api.getBookingSettings = jest.fn().mockRejectedValue(new Error('Load failed'))

    renderWithContexts(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Business Settings')).toBeInTheDocument()
    })

    // Should still render with default values
    expect(screen.getByText('Base Rates (per sq ft)')).toBeInTheDocument()
  })

  it('shows plan-gated features correctly', async () => {
    const basicPlanContext = {
      plan: {
        tier: 'basic',
        features: ['pricing'],
      },
    }

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <PlanContext.Provider value={basicPlanContext}>
          <Settings />
        </PlanContext.Provider>
      </AuthContext.Provider>
    )

    await waitFor(() => {
      expect(screen.getByText('Service Bundles')).toBeInTheDocument()
    })

    // Service bundles section should be disabled for basic plan
    const bundlesSection = screen.getByText('Service Bundles').closest('div')
    expect(bundlesSection).toHaveClass('opacity-50')

    // Seasonal modifiers should be disabled too
    const seasonalSection = screen.getByText('Seasonal Modifiers').closest('div')
    expect(seasonalSection).toHaveClass('opacity-50')
  })

  it('shows tooltips for plan-gated features', async () => {
    const basicPlanContext = {
      plan: {
        tier: 'basic',
        features: ['pricing'],
      },
    }

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <PlanContext.Provider value={basicPlanContext}>
          <Settings />
        </PlanContext.Provider>
      </AuthContext.Provider>
    )

    await waitFor(() => {
      expect(screen.getByText('Service Bundles')).toBeInTheDocument()
    })

    // Hover over disabled bundles section should show tooltip (in real implementation)
    const bundlesSection = screen.getByText('Service Bundles').closest('div')
    fireEvent.mouseEnter(bundlesSection)

    // Note: Testing tooltip visibility would require more complex setup
    // This tests the structure is in place
    expect(bundlesSection).toHaveClass('opacity-50')
  })

  it('toggles auto-reschedule settings correctly', async () => {
    renderWithContexts(<Settings />)

    // Switch to weather tab
    const weatherTab = screen.getByText('Weather')
    fireEvent.click(weatherTab)

    await waitFor(() => {
      expect(screen.getByText('Enable Auto-Reschedule')).toBeInTheDocument()
    })

    // Should show notification hours initially (enabled by default)
    expect(screen.getByText('Notification Hours Ahead')).toBeInTheDocument()

    // Toggle auto-reschedule off
    const autoRescheduleToggle = screen.getByText('Enable Auto-Reschedule').closest('div').querySelector('button')
    fireEvent.click(autoRescheduleToggle)

    // Notification hours should be hidden
    await waitFor(() => {
      expect(screen.queryByText('Notification Hours Ahead')).not.toBeInTheDocument()
    })
  })

  it('toggles quiet hours correctly', async () => {
    renderWithContexts(<Settings />)

    // Switch to booking tab
    const bookingTab = screen.getByText('Booking Policies')
    fireEvent.click(bookingTab)

    await waitFor(() => {
      expect(screen.getByText('Enable Quiet Hours')).toBeInTheDocument()
    })

    // Should show time inputs initially (enabled by default)
    expect(screen.getByLabelText('Start Time')).toBeInTheDocument()
    expect(screen.getByLabelText('End Time')).toBeInTheDocument()

    // Toggle quiet hours off
    const quietHoursToggle = screen.getByText('Enable Quiet Hours').closest('div').querySelector('button')
    fireEvent.click(quietHoursToggle)

    // Time inputs should be hidden
    await waitFor(() => {
      expect(screen.queryByLabelText('Start Time')).not.toBeInTheDocument()
    })
  })

  it('updates business hours for each day correctly', async () => {
    renderWithContexts(<Settings />)

    // Switch to booking tab
    const bookingTab = screen.getByText('Booking Policies')
    fireEvent.click(bookingTab)

    await waitFor(() => {
      expect(screen.getByText('Daily Operating Hours')).toBeInTheDocument()
    })

    // Enable Sunday (disabled by default)
    const sundayCheckbox = screen.getByLabelText('Sunday')
    fireEvent.click(sundayCheckbox)

    // Sunday time inputs should appear
    await waitFor(() => {
      expect(sundayCheckbox).toBeChecked()
    })

    // Disable Monday (enabled by default)
    const mondayCheckbox = screen.getByLabelText('Monday')
    fireEvent.click(mondayCheckbox)

    expect(mondayCheckbox).not.toBeChecked()
  })

  it('handles required fields checkboxes correctly', async () => {
    renderWithContexts(<Settings />)

    // Switch to booking tab
    const bookingTab = screen.getByText('Booking Policies')
    fireEvent.click(bookingTab)

    await waitFor(() => {
      expect(screen.getByText('Required Fields')).toBeInTheDocument()
    })

    // Toggle email field (not required by default)
    const emailCheckbox = screen.getByLabelText('Email')
    fireEvent.click(emailCheckbox)

    expect(emailCheckbox).toBeChecked()

    // Toggle customer name field (required by default)
    const customerNameCheckbox = screen.getByLabelText('Customer Name')
    fireEvent.click(customerNameCheckbox)

    expect(customerNameCheckbox).not.toBeChecked()
  })
})