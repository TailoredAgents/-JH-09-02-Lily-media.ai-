import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Calendar from '../Scheduler'

// Mock dependencies
jest.mock('../../hooks/useApi', () => ({
  useApi: jest.fn()
}))

jest.mock('../../hooks/useEnhancedApi', () => ({
  useEnhancedApi: jest.fn()
}))

jest.mock('../../utils/logger.js', () => ({
  error: jest.fn(),
  debug: jest.fn()
}))

// Mock DragDropCalendar component
jest.mock('../../components/Calendar/DragDropCalendar', () => {
  return function MockDragDropCalendar({ posts, onUpdatePost, onDeletePost, onCreatePost }) {
    return (
      <div data-testid="drag-drop-calendar">
        <div>Calendar Component</div>
        <button onClick={() => onCreatePost({ title: 'Test Post', date: '2023-12-01' })}>
          Create Test Post
        </button>
        <button onClick={() => onUpdatePost(1, { title: 'Updated Post' })}>
          Update Test Post
        </button>
        <button onClick={() => onDeletePost(1)}>
          Delete Test Post
        </button>
        <div data-testid="posts-count">{posts.length} posts</div>
      </div>
    )
  }
})

// Mock CreatePostModal component
jest.mock('../../components/Calendar/CreatePostModal', () => {
  return function MockCreatePostModal({ isOpen, onClose, onCreatePost, selectedDate }) {
    if (!isOpen) return null
    return (
      <div data-testid="create-post-modal">
        <div>Create Post Modal</div>
        <div>Selected Date: {selectedDate}</div>
        <button onClick={() => onCreatePost({ title: 'New Post', date: selectedDate })}>
          Create Post
        </button>
        <button onClick={onClose}>Close Modal</button>
      </div>
    )
  }
})

import { useApi } from '../../hooks/useApi'
import { useEnhancedApi } from '../../hooks/useEnhancedApi'

describe('Calendar Page', () => {
  const mockUseApi = useApi
  const mockUseEnhancedApi = useEnhancedApi
  const mockMakeAuthenticatedRequest = jest.fn()
  const mockMakeEnhancedRequest = jest.fn()
  
  const mockPosts = [
    {
      id: 1,
      title: 'Test Post 1',
      content: 'Test content 1',
      platform: 'LinkedIn',
      date: '2023-12-01',
      time: '09:00',
      status: 'scheduled'
    },
    {
      id: 2,
      title: 'Test Post 2',
      content: 'Test content 2',
      platform: 'Twitter',
      date: '2023-12-02',
      time: '14:00',
      status: 'published'
    }
  ]

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })

  const TestWrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )

  beforeEach(() => {
    jest.clearAllMocks()
    
    mockUseApi.mockReturnValue({
      apiService: {
        getScheduledContent: jest.fn(),
        createContent: jest.fn(),
        updateContent: jest.fn(),
        deleteContent: jest.fn()
      },
      makeAuthenticatedRequest: mockMakeAuthenticatedRequest
    })

    mockUseEnhancedApi.mockReturnValue({
      makeEnhancedRequest: mockMakeEnhancedRequest,
      connectionStatus: 'connected'
    })

    mockMakeAuthenticatedRequest.mockResolvedValue(mockPosts)
  })

  describe('Basic Rendering', () => {
    it('renders calendar page layout', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      expect(screen.getByText('Content Calendar')).toBeInTheDocument()
      expect(screen.getByText('Plan, schedule, and manage your social media content')).toBeInTheDocument()
      expect(screen.getByTestId('drag-drop-calendar')).toBeInTheDocument()
    })

    it('displays loading state initially', () => {
      mockMakeAuthenticatedRequest.mockImplementation(() => new Promise(() => {})) // Never resolves

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      expect(screen.getByText('Loading posts...')).toBeInTheDocument()
    })

    it('displays error state on API failure', async () => {
      mockMakeAuthenticatedRequest.mockRejectedValue(new Error('Failed to load posts'))

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Error loading posts')).toBeInTheDocument()
        expect(screen.getByText('Failed to load posts')).toBeInTheDocument()
      })
    })
  })

  describe('Post Management', () => {
    it('loads and displays posts', async () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByTestId('posts-count')).toHaveTextContent('2 posts')
      })

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalled()
    })

    it('handles post creation', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockPosts) // Initial load
        .mockResolvedValueOnce({ id: 3, title: 'Test Post', date: '2023-12-01' }) // Create response

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByTestId('posts-count')).toHaveTextContent('2 posts')
      })

      const createButton = screen.getByText('Create Test Post')
      fireEvent.click(createButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          { title: 'Test Post', date: '2023-12-01' }
        )
      })
    })

    it('handles post updates', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockPosts) // Initial load
        .mockResolvedValueOnce({ id: 1, title: 'Updated Post' }) // Update response

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByTestId('posts-count')).toHaveTextContent('2 posts')
      })

      const updateButton = screen.getByText('Update Test Post')
      fireEvent.click(updateButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          1,
          { title: 'Updated Post' }
        )
      })
    })

    it('handles post deletion', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockPosts) // Initial load
        .mockResolvedValueOnce({}) // Delete response

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByTestId('posts-count')).toHaveTextContent('2 posts')
      })

      const deleteButton = screen.getByText('Delete Test Post')
      fireEvent.click(deleteButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          1
        )
      })
    })
  })

  describe('Create Post Modal', () => {
    it('opens create post modal', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      const newPostButton = screen.getByRole('button', { name: /new post/i })
      fireEvent.click(newPostButton)

      expect(screen.getByTestId('create-post-modal')).toBeInTheDocument()
    })

    it('closes create post modal', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      // Open modal
      const newPostButton = screen.getByRole('button', { name: /new post/i })
      fireEvent.click(newPostButton)

      expect(screen.getByTestId('create-post-modal')).toBeInTheDocument()

      // Close modal
      const closeButton = screen.getByText('Close Modal')
      fireEvent.click(closeButton)

      expect(screen.queryByTestId('create-post-modal')).not.toBeInTheDocument()
    })

    it('creates post through modal', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockPosts) // Initial load
        .mockResolvedValueOnce({ id: 3, title: 'New Post' }) // Create response

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      // Open modal
      const newPostButton = screen.getByRole('button', { name: /new post/i })
      fireEvent.click(newPostButton)

      // Create post through modal
      const createPostButton = screen.getByText('Create Post')
      fireEvent.click(createPostButton)

      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
          expect.any(Function),
          expect.objectContaining({ title: 'New Post' })
        )
      })
    })
  })

  describe('Filter and View Controls', () => {
    it('displays filter controls', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      expect(screen.getByText('All Platforms')).toBeInTheDocument()
      expect(screen.getByText('All Status')).toBeInTheDocument()
    })

    it('handles platform filter changes', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      const platformFilter = screen.getByDisplayValue('all')
      fireEvent.change(platformFilter, { target: { value: 'linkedin' } })

      expect(platformFilter.value).toBe('linkedin')
    })

    it('handles status filter changes', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      const statusFilter = screen.getByDisplayValue('all')
      fireEvent.change(statusFilter, { target: { value: 'scheduled' } })

      expect(statusFilter.value).toBe('scheduled')
    })

    it('displays view toggle buttons', () => {
      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      expect(screen.getByRole('button', { name: /week/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /month/i })).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows retry option on error', async () => {
      mockMakeAuthenticatedRequest.mockRejectedValue(new Error('Network error'))

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Error loading posts')).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: /retry/i })
      expect(retryButton).toBeInTheDocument()
    })

    it('retries loading posts on retry button click', async () => {
      mockMakeAuthenticatedRequest
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockPosts)

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('Error loading posts')).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: /retry/i })
      fireEvent.click(retryButton)

      await waitFor(() => {
        expect(screen.getByTestId('posts-count')).toHaveTextContent('2 posts')
      })
    })

    it('handles create post errors gracefully', async () => {
      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(mockPosts) // Initial load
        .mockRejectedValueOnce(new Error('Create failed')) // Create error

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByTestId('posts-count')).toHaveTextContent('2 posts')
      })

      const createButton = screen.getByText('Create Test Post')
      fireEvent.click(createButton)

      // Should handle error gracefully without crashing
      await waitFor(() => {
        expect(mockMakeAuthenticatedRequest).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Responsive Design', () => {
    it('adapts to mobile viewport', () => {
      // Mock window size
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      })

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      expect(screen.getByText('Content Calendar')).toBeInTheDocument()
      // Mobile-specific elements would be tested here
    })

    it('shows full features on desktop', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      })

      render(
        <TestWrapper>
          <Calendar />
        </TestWrapper>
      )

      expect(screen.getByText('Content Calendar')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /new post/i })).toBeInTheDocument()
    })
  })
})