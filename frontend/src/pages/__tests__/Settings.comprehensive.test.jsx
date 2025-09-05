import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Settings from '../Settings'

// Mock dependencies
jest.mock('../../hooks/useApi', () => ({
  useApi: jest.fn(),
}))

jest.mock('../../hooks/useNotifications', () => ({
  useNotifications: jest.fn(),
}))

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}))

jest.mock('../../utils/logger.js', () => ({
  error: jest.fn(),
  info: jest.fn(),
}))

import { useApi } from '../../hooks/useApi'
import { useNotifications } from '../../hooks/useNotifications'
import { useAuth } from '../../contexts/AuthContext'

describe('Settings Page', () => {
  const mockUseApi = useApi
  const mockUseNotifications = useNotifications
  const mockUseAuth = useAuth
  const mockMakeAuthenticatedRequest = jest.fn()
  const mockShowSuccess = jest.fn()
  const mockShowError = jest.fn()

  const mockSettings = {
    profile: {
      name: 'John Doe',
      email: 'john@example.com',
      company: 'Tech Corp',
      timezone: 'America/New_York',
      language: 'en',
    },
    notifications: {
      email_notifications: true,
      push_notifications: false,
      weekly_reports: true,
      performance_alerts: true,
    },
    privacy: {
      data_sharing: false,
      analytics_tracking: true,
      third_party_integrations: true,
    },
    billing: {
      plan: 'Pro',
      billing_cycle: 'monthly',
      next_billing_date: '2024-01-15',
      payment_method: '**** 1234',
    },
    integrations: {
      twitter: { connected: true, username: '@johndoe' },
      linkedin: { connected: true, username: 'John Doe' },
      instagram: { connected: false, username: null },
      facebook: { connected: true, username: 'John Doe' },
    },
  }

  const mockUser = {
    name: 'John Doe',
    email: 'john@example.com',
    picture: 'https://example.com/avatar.jpg',
  }

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  const TestWrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )

  beforeEach(() => {
    jest.clearAllMocks()

    mockUseApi.mockReturnValue({
      apiService: {
        getUserSettings: jest.fn(),
        updateUserSettings: jest.fn(),
        connectPlatform: jest.fn(),
        disconnectPlatform: jest.fn(),
        updateBilling: jest.fn(),
      },
      makeAuthenticatedRequest: mockMakeAuthenticatedRequest,
    })

    mockUseNotifications.mockReturnValue({
      showSuccess: mockShowSuccess,
      showError: mockShowError,
    })

    mockUseAuth.mockReturnValue({
      userProfile: mockUser,
      logout: jest.fn(),
    })

    mockMakeAuthenticatedRequest.mockResolvedValue(mockSettings)
  })

  describe('Basic Rendering', () => {
    it('renders settings page layout', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      expect(screen.getByText('Settings')).toBeInTheDocument()
      expect(
        screen.getByText('Manage your account preferences and integrations')
      ).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('Profile')).toBeInTheDocument()
        expect(screen.getByText('Notifications')).toBeInTheDocument()
        expect(screen.getByText('Privacy')).toBeInTheDocument()
        expect(screen.getByText('Billing')).toBeInTheDocument()
        expect(screen.getByText('Integrations')).toBeInTheDocument()
      })
    })

    it('displays loading state initially', () => {
      mockMakeAuthenticatedRequest.mockImplementation(
        () => new Promise(() => {})
      )

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      expect(screen.getByText('Loading settings...')).toBeInTheDocument()
    })

    it('displays error state on API failure', async () => {
      mockMakeAuthenticatedRequest.mockRejectedValue(
        new Error('Failed to load settings')
      )

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Error loading settings')).toBeInTheDocument()
      })
    })
  })

  describe('Profile Settings', () => {
    it('displays profile information', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
        expect(screen.getByDisplayValue('john@example.com')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Tech Corp')).toBeInTheDocument()
      })
    })

    it('allows editing profile information', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
      })

      const nameInput = screen.getByDisplayValue('John Doe')
      fireEvent.change(nameInput, { target: { value: 'John Smith' } })

      expect(nameInput.value).toBe('John Smith')
    })

    it('saves profile changes', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockSettings) // Initial load
        .mockResolvedValueOnce({ success: true }) // Save response

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
      })

      const nameInput = screen.getByDisplayValue('John Doe')
      fireEvent.change(nameInput, { target: { value: 'John Smith' } })

      const saveButton = screen.getByRole('button', { name: /save profile/i })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          expect.objectContaining({
            profile: expect.objectContaining({
              name: 'John Smith',
            }),
          })
        )
      })
    })

    it('handles timezone selection', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('America/New_York')).toBeInTheDocument()
      })

      const timezoneSelect = screen.getByDisplayValue('America/New_York')
      fireEvent.change(timezoneSelect, { target: { value: 'Europe/London' } })

      expect(timezoneSelect.value).toBe('Europe/London')
    })
  })

  describe('Notification Settings', () => {
    it('displays notification preferences', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const emailNotifications = screen.getByRole('checkbox', {
          name: /email notifications/i,
        })
        const pushNotifications = screen.getByRole('checkbox', {
          name: /push notifications/i,
        })

        expect(emailNotifications).toBeChecked()
        expect(pushNotifications).not.toBeChecked()
      })
    })

    it('toggles notification settings', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('checkbox', { name: /email notifications/i })
        ).toBeInTheDocument()
      })

      const emailCheckbox = screen.getByRole('checkbox', {
        name: /email notifications/i,
      })
      fireEvent.click(emailCheckbox)

      expect(emailCheckbox).not.toBeChecked()
    })

    it('saves notification preferences', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockSettings) // Initial load
        .mockResolvedValueOnce({ success: true }) // Save response

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('checkbox', { name: /email notifications/i })
        ).toBeInTheDocument()
      })

      const emailCheckbox = screen.getByRole('checkbox', {
        name: /email notifications/i,
      })
      fireEvent.click(emailCheckbox)

      const saveButton = screen.getByRole('button', {
        name: /save notifications/i,
      })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          expect.objectContaining({
            notifications: expect.objectContaining({
              email_notifications: false,
            }),
          })
        )
      })
    })
  })

  describe('Privacy Settings', () => {
    it('displays privacy preferences', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        const dataSharing = screen.getByRole('checkbox', {
          name: /data sharing/i,
        })
        const analyticsTracking = screen.getByRole('checkbox', {
          name: /analytics tracking/i,
        })

        expect(dataSharing).not.toBeChecked()
        expect(analyticsTracking).toBeChecked()
      })
    })

    it('toggles privacy settings', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('checkbox', { name: /data sharing/i })
        ).toBeInTheDocument()
      })

      const dataSharingCheckbox = screen.getByRole('checkbox', {
        name: /data sharing/i,
      })
      fireEvent.click(dataSharingCheckbox)

      expect(dataSharingCheckbox).toBeChecked()
    })
  })

  describe('Platform Integrations', () => {
    it('displays connected platforms', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Twitter')).toBeInTheDocument()
        expect(screen.getByText('@johndoe')).toBeInTheDocument()
        expect(screen.getByText('Connected')).toBeInTheDocument()
      })
    })

    it('displays disconnected platforms', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Instagram')).toBeInTheDocument()
        expect(screen.getByText('Not Connected')).toBeInTheDocument()
      })
    })

    it('connects a platform', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockSettings) // Initial load
        .mockResolvedValueOnce({
          success: true,
          auth_url: 'https://instagram.com/oauth/authorize',
        }) // Connect response

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Instagram')).toBeInTheDocument()
      })

      const connectButton = screen.getByRole('button', {
        name: /connect instagram/i,
      })
      fireEvent.click(connectButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          'instagram'
        )
      })
    })

    it('disconnects a platform', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockSettings) // Initial load
        .mockResolvedValueOnce({ success: true }) // Disconnect response

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Twitter')).toBeInTheDocument()
      })

      const disconnectButton = screen.getByRole('button', {
        name: /disconnect twitter/i,
      })
      fireEvent.click(disconnectButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          'twitter'
        )
      })
    })
  })

  describe('Billing Information', () => {
    it('displays billing details', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Pro Plan')).toBeInTheDocument()
        expect(screen.getByText('Monthly billing')).toBeInTheDocument()
        expect(screen.getByText('**** 1234')).toBeInTheDocument()
      })
    })

    it('shows next billing date', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/January 15, 2024/)).toBeInTheDocument()
      })
    })

    it('provides plan upgrade option', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /upgrade plan/i })
        ).toBeInTheDocument()
      })
    })

    it('provides payment method update option', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /update payment/i })
        ).toBeInTheDocument()
      })
    })
  })

  describe('Account Management', () => {
    it('provides export data option', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /export data/i })
        ).toBeInTheDocument()
      })
    })

    it('provides delete account option', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /delete account/i })
        ).toBeInTheDocument()
      })
    })

    it('shows confirmation for destructive actions', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /delete account/i })
        ).toBeInTheDocument()
      })

      const deleteButton = screen.getByRole('button', {
        name: /delete account/i,
      })
      fireEvent.click(deleteButton)

      expect(
        screen.getByText('Are you sure you want to delete your account?')
      ).toBeInTheDocument()
    })
  })

  describe('Error Handling and Success Messages', () => {
    it('shows success message on settings save', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockSettings) // Initial load
        .mockResolvedValueOnce({ success: true }) // Save response

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
      })

      const saveButton = screen.getByRole('button', { name: /save profile/i })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockShowSuccess).toHaveBeenCalledWith(
          'Settings saved successfully'
        )
      })
    })

    it('shows error message on settings save failure', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockSettings) // Initial load
        .mockRejectedValueOnce(new Error('Save failed')) // Save error

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
      })

      const saveButton = screen.getByRole('button', { name: /save profile/i })
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockShowError).toHaveBeenCalledWith('Failed to save settings')
      })
    })

    it('handles network errors gracefully', async () => {
      mockMakeAuthenticatedRequest.mockRejectedValue(new Error('Network error'))

      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Error loading settings')).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: /retry/i })
      expect(retryButton).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('validates required fields', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
      })

      const nameInput = screen.getByDisplayValue('John Doe')
      fireEvent.change(nameInput, { target: { value: '' } })

      const saveButton = screen.getByRole('button', { name: /save profile/i })
      fireEvent.click(saveButton)

      expect(screen.getByText('Name is required')).toBeInTheDocument()
    })

    it('validates email format', async () => {
      render(
        <TestWrapper>
          <Settings />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('john@example.com')).toBeInTheDocument()
      })

      const emailInput = screen.getByDisplayValue('john@example.com')
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })

      const saveButton = screen.getByRole('button', { name: /save profile/i })
      fireEvent.click(saveButton)

      expect(
        screen.getByText('Please enter a valid email address')
      ).toBeInTheDocument()
    })
  })
})
