import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom'

import Login from '../Login'
import { AuthProvider } from '../../contexts/AuthContext'

// Mock fetch for API calls
global.fetch = jest.fn()

// Mock router
const mockNavigate = jest.fn()
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  Link: ({ children, to, ...props }) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}))

const renderWithProviders = (ui, options = {}) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  const AllTheProviders = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>{children}</BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )

  return render(ui, { wrapper: AllTheProviders, ...options })
}

describe('Login Component', () => {
  beforeEach(() => {
    fetch.mockClear()
    mockNavigate.mockClear()
    localStorage.clear()
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  test('renders login form correctly', () => {
    renderWithProviders(<Login />)

    expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByText(/create account/i)).toBeInTheDocument()
    expect(screen.getByText(/forgot password/i)).toBeInTheDocument()
  })

  test('handles successful login', async () => {
    const user = userEvent.setup()

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'mock-token',
        user: { id: 1, email: 'test@example.com', name: 'Test User' },
      }),
    })

    renderWithProviders(<Login />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/auth/login',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
          }),
        })
      )
    })

    expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
  })

  test('handles login validation errors', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
  })

  test('handles invalid email format', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)

    await user.type(screen.getByLabelText(/email/i), 'invalid-email')
    await user.type(screen.getByLabelText(/password/i), 'password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument()
  })

  test('handles API error responses', async () => {
    const user = userEvent.setup()

    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid credentials' }),
    })

    renderWithProviders(<Login />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  test('handles network errors', async () => {
    const user = userEvent.setup()

    fetch.mockRejectedValueOnce(new Error('Network error'))

    renderWithProviders(<Login />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })

  test('shows loading state during login', async () => {
    const user = userEvent.setup()

    fetch.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    )

    renderWithProviders(<Login />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByText(/signing in/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })

  test('password visibility toggle works', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)

    const passwordInput = screen.getByLabelText(/password/i)
    const toggleButton = screen.getByRole('button', { name: /show password/i })

    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'text')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  test('form submission prevents default browser behavior', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)

    const form = screen
      .getByRole('button', { name: /sign in/i })
      .closest('form')
    const submitHandler = jest.fn((e) => e.preventDefault())
    form.addEventListener('submit', submitHandler)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    fireEvent.submit(form)

    expect(submitHandler).toHaveBeenCalled()
  })

  test('focuses first input on mount', () => {
    renderWithProviders(<Login />)
    expect(screen.getByLabelText(/email/i)).toHaveFocus()
  })

  test('keyboard navigation works correctly', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Login />)

    expect(screen.getByLabelText(/email/i)).toHaveFocus()

    await user.tab()
    expect(screen.getByLabelText(/password/i)).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: /show password/i })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: /sign in/i })).toHaveFocus()
  })
})
