import React from 'react'
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HelmetProvider } from 'react-helmet-async'

// Context Providers
import { AuthProvider } from './contexts/AuthContext'
import { AdminAuthProvider } from './contexts/AdminAuthContext'
import { WebSocketProvider } from './contexts/WebSocketContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { PlanProvider } from './contexts/PlanContext'

// Error handling
import { ErrorBoundary } from './utils/errorReporter.jsx'

// Components
import Layout from './components/Layout'
import AdminLayout from './components/AdminLayout'
import ProtectedRoute from './components/ProtectedRoute'
import PublicRoute from './components/PublicRoute'
import AdminProtectedRoute from './components/AdminProtectedRoute'
import RealTimeNotificationContainer from './components/Notifications/RealTimeNotificationContainer'

// Pages
import LandingPage from './pages/LandingPage'
import Login from './pages/Login'
import Register from './pages/Register'
import EmailVerification from './pages/EmailVerification'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Overview from './pages/Overview'
import CreatePost from './pages/CreatePost'
import Scheduler from './pages/Scheduler'
import Content from './pages/Content'
import MemoryExplorer from './pages/MemoryExplorer'
import SocialInbox from './pages/SocialInbox'
import Settings from './pages/Settings'
import ErrorLogs from './components/ErrorLogs'

// Conditionally import Integrations page if feature is enabled
const Integrations =
  import.meta.env.VITE_FEATURE_PARTNER_OAUTH === 'true'
    ? React.lazy(() => import('./pages/Integrations'))
    : null

// Admin Pages
import AdminLogin from './pages/admin/AdminLogin'
import AdminDashboard from './pages/admin/AdminDashboard'
import UserManagement from './pages/admin/UserManagement'

// Error Pages
import NotFound from './pages/errors/NotFound'
import Forbidden from './pages/errors/Forbidden'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10 * 60 * 1000, // 10 minutes - keep cached longer
      cacheTime: 30 * 60 * 1000, // 30 minutes
      retry: 0, // Disable retries to prevent CORS cascades
      refetchOnWindowFocus: false,
      refetchOnReconnect: false, // Don't refetch when reconnecting
      refetchInterval: false, // Disable automatic refetching
      enabled: true, // Can be controlled per query
    },
  },
})

// No authentication configuration needed

function AppRoutes() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        {/* Admin Routes */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route
          path="/admin/dashboard"
          element={
            <AdminProtectedRoute>
              <AdminLayout>
                <AdminDashboard />
              </AdminLayout>
            </AdminProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <AdminProtectedRoute>
              <AdminLayout>
                <UserManagement />
              </AdminLayout>
            </AdminProtectedRoute>
          }
        />
        <Route
          path="/admin/*"
          element={
            <AdminProtectedRoute>
              <AdminLayout>
                <div className="text-center py-12">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Page Under Development
                  </h3>
                  <p className="text-sm text-gray-500">
                    This admin feature is coming soon.
                  </p>
                </div>
              </AdminLayout>
            </AdminProtectedRoute>
          }
        />

        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          }
        />
        <Route path="/email-verification" element={<EmailVerification />} />
        <Route
          path="/forgot-password"
          element={
            <PublicRoute>
              <ForgotPassword />
            </PublicRoute>
          }
        />
        <Route
          path="/reset-password"
          element={
            <PublicRoute>
              <ResetPassword />
            </PublicRoute>
          }
        />

        {/* Protected User Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Layout>
                <Overview />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/create-post"
          element={
            <ProtectedRoute>
              <Layout>
                <CreatePost />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/calendar"
          element={
            <ProtectedRoute>
              <Layout>
                <Scheduler />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/content"
          element={
            <ProtectedRoute>
              <Layout>
                <Content />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/memory"
          element={
            <ProtectedRoute>
              <Layout>
                <MemoryExplorer />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/inbox"
          element={
            <ProtectedRoute>
              <Layout>
                <SocialInbox />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/billing"
          element={
            <ProtectedRoute>
              <Layout>
                <React.Suspense
                  fallback={
                    <div className="flex items-center justify-center min-h-screen">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      <span className="ml-3 text-gray-600">
                        Loading Billing...
                      </span>
                    </div>
                  }
                >
                  {React.createElement(
                    React.lazy(() => import('./pages/Billing'))
                  )}
                </React.Suspense>
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Layout>
                <Settings />
              </Layout>
            </ProtectedRoute>
          }
        />
        {/* Integrations Route - Feature Flag Gated */}
        {import.meta.env.VITE_FEATURE_PARTNER_OAUTH === 'true' &&
          Integrations && (
            <Route
              path="/integrations"
              element={
                <ProtectedRoute>
                  <Layout>
                    <React.Suspense
                      fallback={
                        <div className="flex items-center justify-center min-h-screen">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                          <span className="ml-3 text-gray-600">
                            Loading Integrations...
                          </span>
                        </div>
                      }
                    >
                      <Integrations />
                    </React.Suspense>
                  </Layout>
                </ProtectedRoute>
              }
            />
          )}
        <Route
          path="/error-logs"
          element={
            <ProtectedRoute>
              <Layout>
                <ErrorLogs />
              </Layout>
            </ProtectedRoute>
          }
        />

        {/* Error Pages */}
        <Route path="/403" element={<Forbidden />} />
        <Route path="/forbidden" element={<Forbidden />} />

        {/* 404 - Must be last */}
        <Route path="*" element={<NotFound />} />
      </Routes>

      {/* Real-time Notification System */}
      <RealTimeNotificationContainer />
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <HelmetProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <AdminAuthProvider>
              <AuthProvider>
                <PlanProvider>
                  <WebSocketProvider>
                    <Router>
                      <AppRoutes />
                    </Router>
                  </WebSocketProvider>
                </PlanProvider>
              </AuthProvider>
            </AdminAuthProvider>
          </ThemeProvider>
        </QueryClientProvider>
      </HelmetProvider>
    </ErrorBoundary>
  )
}

export default App
