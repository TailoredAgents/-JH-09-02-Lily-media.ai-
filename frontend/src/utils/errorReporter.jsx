import React from 'react';
import apiService from '../services/api';

class ErrorReporter {
  constructor() {
    this.setupErrorHandlers();
    this.errorQueue = [];
    this.localErrors = this.loadLocalErrors();
    this.isOnline = navigator.onLine;
    this.maxLocalErrors = 1000;
    
    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.flushErrorQueue();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  // Load errors from localStorage
  loadLocalErrors() {
    try {
      const stored = localStorage.getItem('aiSocial_errorLogs');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.warn('Failed to load local errors:', e);
      return [];
    }
  }

  // Save errors to localStorage
  saveLocalErrors() {
    try {
      // Keep only the most recent errors
      const errors = this.localErrors.slice(0, this.maxLocalErrors);
      localStorage.setItem('aiSocial_errorLogs', JSON.stringify(errors));
    } catch (e) {
      console.warn('Failed to save local errors:', e);
    }
  }

  // Get local errors (for displaying when backend is down)
  getLocalErrors(limit = 100) {
    return this.localErrors.slice(0, limit);
  }

  // Clear local errors
  clearLocalErrors() {
    this.localErrors = [];
    localStorage.removeItem('aiSocial_errorLogs');
  }

  setupErrorHandlers() {
    // Global error handler
    window.addEventListener('error', (event) => {
      this.reportError({
        message: event.message,
        source: event.filename,
        line: event.lineno,
        column: event.colno,
        error: event.error,
        type: 'javascript-error'
      });
    });

    // Promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.reportError({
        message: event.reason?.message || event.reason || 'Unhandled Promise Rejection',
        error: event.reason,
        type: 'unhandled-rejection'
      });
    });

    // React Error Boundary errors are handled separately
  }

  reportError(errorData) {
    // Skip CORS errors to prevent infinite loops
    if (errorData.message && (
      errorData.message.includes('CORS') ||
      errorData.message.includes('Cross-Origin') ||
      errorData.message.includes('blocked by CORS') ||
      errorData.message.includes('Access-Control-Allow-Origin')
    )) {
      console.warn('CORS error detected, skipping error reporting to prevent loops');
      return;
    }

    const error = {
      ...errorData,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      screen: {
        width: window.screen.width,
        height: window.screen.height
      },
      id: Date.now() + Math.random()
    };

    // Add stack trace if available
    if (errorData.error && errorData.error.stack) {
      error.stack = errorData.error.stack;
    }

    // Always store locally first
    this.localErrors.unshift(error);
    this.saveLocalErrors();

    // Also add to queue for backend
    this.errorQueue.push(error);

    // Try to send immediately if online
    if (this.isOnline) {
      this.flushErrorQueue();
    }

    // Log to console as well
    console.error('Error captured:', error);
  }

  async flushErrorQueue() {
    // Temporarily disabled to prevent 405 log spam
    if (this.errorQueue.length > 0) {
      console.log(`Suppressed ${this.errorQueue.length} error reports to prevent log spam`);
      this.errorQueue = [];
    }
    return;
    
    if (this.errorQueue.length === 0) return;

    // Circuit breaker - if we've failed too many times, stop trying
    if (this.failureCount > 3) {  // Reduced threshold to prevent CORS loops
      console.warn('Error reporting disabled - too many failures');
      this.errorQueue = []; // Clear queue to prevent memory leak
      return;
    }

    const errors = [...this.errorQueue];
    this.errorQueue = [];
    
    // Use bounded concurrency for better performance
    const maxConcurrent = 5;
    let i = 0;
    
    const worker = async () => {
      while (i < errors.length) {
        const idx = i++; // take next
        try {
          await apiService.request('/api/system/logs/error', {
            method: 'POST',
            body: errors[idx]
          });
          this.failureCount = 0; // Reset on success
        } catch (e) {
          this.failureCount = (this.failureCount || 0) + 1;
          
          // Don't re-queue if we're failing too much
          if (this.failureCount <= 2) {
            this.errorQueue.push(errors[idx]);
          }
          
          // Don't log errors about error reporting (prevents loops)
          if (!e.message.includes('/api/system/logs/error')) {
            console.error('Failed to report error:', e);
          }
        }
      }
    };
    
    // Run workers concurrently with bounded parallelism
    await Promise.allSettled(
      Array.from({ length: Math.min(maxConcurrent, errors.length) }, worker)
    );
    
    if (this.failureCount > 3) {
      console.warn('Error reporting disabled - too many failures');
    }
  }

  // Manual error reporting
  logError(message, details = {}) {
    this.reportError({
      message,
      ...details,
      type: 'manual-log'
    });
  }

  // Network error reporting
  logNetworkError(url, method, status, error) {
    // Skip reporting auth failures to prevent infinite loops
    if (status === 401 || status === 403) {
      console.warn(`Auth failure ${status} for ${method} ${url} - skipping error report to prevent loops`);
      return;
    }
    
    // Skip rate limiting errors since they're expected
    if (status === 429) {
      console.warn(`Rate limit ${status} for ${method} ${url} - skipping error report`);
      return;
    }
    
    this.reportError({
      message: `Network error: ${method} ${url} - ${status}`,
      endpoint: url,
      method,
      status,
      error: error?.message || error,
      type: 'network-error'
    });
  }

  // Performance issue reporting
  logPerformanceIssue(metric, value, threshold) {
    if (value > threshold) {
      this.reportError({
        message: `Performance issue: ${metric} exceeded threshold`,
        metric,
        value,
        threshold,
        type: 'performance-issue',
        severity: 'warning'
      });
    }
  }
}

// Create singleton instance
const errorReporter = new ErrorReporter();

// Export for use in React components
export default errorReporter;

// React Error Boundary
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    errorReporter.reportError({
      message: error.toString(),
      componentStack: errorInfo.componentStack,
      error,
      type: 'react-error-boundary'
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
          <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h2>
            <p className="text-gray-600 mb-4">
              An error occurred while rendering this component. The error has been logged.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}