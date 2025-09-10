import React from 'react'
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { error as logError } from '../../utils/logger.js'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null
    }
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { 
      hasError: true,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }
  }

  componentDidCatch(error, errorInfo) {
    // Log the error details
    logError('React Error Boundary caught an error:', error, {
      errorInfo,
      errorId: this.state.errorId,
      component: this.props.componentName || 'Unknown',
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    })

    this.setState({
      error: error,
      errorInfo: errorInfo
    })

    // Send error to monitoring service if available
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  handleRetry = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null
    })
    
    if (this.props.onRetry) {
      this.props.onRetry()
    }
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleRetry)
      }

      // Default error UI
      return (
        <div 
          className="min-h-96 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200"
          role="alert"
          aria-labelledby="error-boundary-title"
          aria-describedby="error-boundary-message"
        >
          <div className="text-center p-8">
            <ExclamationTriangleIcon 
              className="mx-auto h-16 w-16 text-red-500 mb-4" 
              aria-hidden="true"
            />
            <h3 
              id="error-boundary-title"
              className="text-lg font-medium text-gray-900 mb-2"
            >
              {this.props.title || 'Something went wrong'}
            </h3>
            <p 
              id="error-boundary-message"
              className="text-sm text-gray-600 mb-6 max-w-md"
            >
              {this.props.message || 'We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.'}
            </p>
            
            {this.props.showDetails && this.state.error && (
              <details className="text-left bg-gray-100 p-4 rounded-md mb-6 max-w-lg mx-auto">
                <summary className="cursor-pointer text-sm font-medium text-gray-700 mb-2">
                  Error Details
                </summary>
                <div className="text-xs text-gray-600 font-mono">
                  <p><strong>Error:</strong> {this.state.error.toString()}</p>
                  <p><strong>Error ID:</strong> {this.state.errorId}</p>
                  <p><strong>Component:</strong> {this.props.componentName || 'Unknown'}</p>
                  {this.state.errorInfo && (
                    <>
                      <p><strong>Component Stack:</strong></p>
                      <pre className="whitespace-pre-wrap text-xs mt-1">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                </div>
              </details>
            )}

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                aria-label="Retry the operation that caused the error"
                type="button"
              >
                <ArrowPathIcon className="h-4 w-4 mr-2" aria-hidden="true" />
                Try Again
              </button>
              
              {this.props.showRefresh && (
                <button
                  onClick={() => window.location.reload()}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  aria-label="Refresh the page to reload the application"
                  type="button"
                >
                  Refresh Page
                </button>
              )}
            </div>

            {this.props.supportContact && (
              <p className="text-xs text-gray-500 mt-4">
                Error ID: {this.state.errorId}
                <br />
                If you need help, please contact support with this error ID.
              </p>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary