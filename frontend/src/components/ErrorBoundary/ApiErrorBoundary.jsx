import React from 'react'
import ErrorBoundary from './ErrorBoundary'
import { WifiIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

const ApiErrorFallback = (error, retry) => {
  const isNetworkError = error?.message?.includes('Network') || 
                        error?.message?.includes('fetch') ||
                        error?.message?.includes('ERR_NETWORK')
  
  const isAuthError = error?.message?.includes('401') || 
                     error?.message?.includes('Unauthorized') ||
                     error?.message?.includes('Authentication')

  const is429Error = error?.message?.includes('429') || 
                    error?.message?.includes('rate limit')

  const is503Error = error?.message?.includes('503') || 
                    error?.message?.includes('Service Unavailable')

  let title, message, actionText, ariaLabel

  if (isNetworkError) {
    title = 'Connection Problem'
    message = 'Unable to connect to our servers. Please check your internet connection and try again.'
    actionText = 'Retry Connection'
    ariaLabel = 'Retry connection to server'
  } else if (isAuthError) {
    title = 'Authentication Required'
    message = 'Your session has expired. Please refresh the page to log in again.'
    actionText = 'Refresh Page'
    ariaLabel = 'Refresh page to authenticate'
  } else if (is429Error) {
    title = 'Too Many Requests'
    message = 'You\'re making requests too quickly. Please wait a moment before trying again.'
    actionText = 'Try Again'
    ariaLabel = 'Try API request again'
  } else if (is503Error) {
    title = 'Service Temporarily Unavailable'
    message = 'Our servers are currently experiencing high traffic. Please try again in a few minutes.'
    actionText = 'Retry'
    ariaLabel = 'Retry when service is available'
  } else {
    title = 'API Error'
    message = 'We encountered an error while loading data. This might be a temporary issue.'
    actionText = 'Retry'
    ariaLabel = 'Retry API request'
  }

  // Announce error to screen readers
  React.useEffect(() => {
    const announcement = `${title}: ${message}`
    const liveRegion = document.createElement('div')
    liveRegion.setAttribute('aria-live', 'assertive')
    liveRegion.setAttribute('aria-atomic', 'true')
    liveRegion.setAttribute('class', 'sr-only')
    liveRegion.textContent = announcement
    document.body.appendChild(liveRegion)

    // Remove after announcement
    const timer = setTimeout(() => {
      if (document.body.contains(liveRegion)) {
        document.body.removeChild(liveRegion)
      }
    }, 3000)

    return () => {
      clearTimeout(timer)
      if (document.body.contains(liveRegion)) {
        document.body.removeChild(liveRegion)
      }
    }
  }, [title, message])

  return (
    <div 
      className="min-h-64 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200"
      role="alert"
      aria-labelledby="api-error-title"
      aria-describedby="api-error-message"
    >
      <div className="text-center p-6">
        {isNetworkError ? (
          <WifiIcon 
            className="mx-auto h-12 w-12 text-orange-500 mb-3" 
            aria-hidden="true"
          />
        ) : (
          <ExclamationTriangleIcon 
            className="mx-auto h-12 w-12 text-red-500 mb-3" 
            aria-hidden="true"
          />
        )}
        
        <h3 
          id="api-error-title"
          className="text-lg font-medium text-gray-900 mb-2"
        >
          {title}
        </h3>
        <p 
          id="api-error-message"
          className="text-sm text-gray-600 mb-4 max-w-sm"
        >
          {message}
        </p>
        
        <button
          onClick={retry}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          aria-label={ariaLabel}
          type="button"
        >
          {actionText}
        </button>
      </div>
    </div>
  )
}

const ApiErrorBoundary = ({ children, componentName, onError, onRetry }) => {
  return (
    <ErrorBoundary
      componentName={componentName}
      fallback={ApiErrorFallback}
      onError={onError}
      onRetry={onRetry}
      title="API Error"
      message="Failed to load data from the server."
      showRefresh={true}
      supportContact={true}
    >
      {children}
    </ErrorBoundary>
  )
}

export default ApiErrorBoundary