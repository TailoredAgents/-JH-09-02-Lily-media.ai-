import React from 'react'
import ErrorBoundary from './ErrorBoundary'
import { HomeIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

const PageErrorFallback = (error, retry) => {
  const navigateHome = () => {
    // Announce navigation to screen readers
    const liveRegion = document.createElement('div')
    liveRegion.setAttribute('aria-live', 'assertive')
    liveRegion.setAttribute('class', 'sr-only')
    liveRegion.textContent = 'Navigating to homepage...'
    document.body.appendChild(liveRegion)
    
    setTimeout(() => {
      window.location.href = '/'
    }, 1000)
  }

  const handleRetry = () => {
    // Announce retry attempt to screen readers
    const liveRegion = document.createElement('div')
    liveRegion.setAttribute('aria-live', 'assertive')
    liveRegion.setAttribute('class', 'sr-only')
    liveRegion.textContent = 'Retrying page load...'
    document.body.appendChild(liveRegion)
    
    setTimeout(() => {
      retry()
    }, 500)
  }

  // Announce error to screen readers
  React.useEffect(() => {
    const announcement = 'Page error occurred. This page encountered an unexpected error. You can try reloading the page or return to the dashboard.'
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

    // Update document title for screen readers
    const originalTitle = document.title
    document.title = 'Page Error - Lily AI Social Media'

    return () => {
      clearTimeout(timer)
      if (document.body.contains(liveRegion)) {
        document.body.removeChild(liveRegion)
      }
      document.title = originalTitle
    }
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      {/* Skip Link for Screen Readers */}
      <a
        href="#page-error-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:z-50"
      >
        Skip to error content
      </a>

      <main 
        id="page-error-content"
        className="text-center p-8 max-w-md"
        role="main"
        aria-labelledby="page-error-title"
        aria-describedby="page-error-message"
      >
        <div 
          className="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-red-100 mb-6"
          role="img"
          aria-label="Page error"
        >
          <HomeIcon className="h-10 w-10 text-red-600" aria-hidden="true" />
        </div>
        
        <h1 
          id="page-error-title"
          className="text-2xl font-bold text-gray-900 mb-3"
        >
          Page Error
        </h1>
        
        <p 
          id="page-error-message"
          className="text-gray-600 mb-8"
        >
          This page encountered an unexpected error. You can try reloading the page 
          or return to the dashboard.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={handleRetry}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            aria-describedby="retry-description"
            type="button"
          >
            <ArrowPathIcon className="h-5 w-5 mr-2" aria-hidden="true" />
            Try Again
          </button>
          <p id="retry-description" className="sr-only">
            This will attempt to reload the current page
          </p>
          
          <button
            onClick={navigateHome}
            className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            aria-describedby="home-description"
            type="button"
          >
            <HomeIcon className="h-5 w-5 mr-2" aria-hidden="true" />
            Go to Dashboard
          </button>
          <p id="home-description" className="sr-only">
            This will take you to the main dashboard page
          </p>
        </div>

        {/* Additional Context for Screen Readers */}
        <div className="sr-only">
          <p>
            You have encountered a page error. The error has been reported automatically. 
            You can try reloading the current page or navigate to the dashboard to continue 
            using the application.
          </p>
        </div>
      </main>
    </div>
  )
}

const PageErrorBoundary = ({ children, pageName, onError, onRetry }) => {
  return (
    <ErrorBoundary
      componentName={`Page: ${pageName}`}
      fallback={PageErrorFallback}
      onError={onError}
      onRetry={onRetry}
      showDetails={true}
      showRefresh={true}
      supportContact={true}
    >
      {children}
    </ErrorBoundary>
  )
}

export default PageErrorBoundary