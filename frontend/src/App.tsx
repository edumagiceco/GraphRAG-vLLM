/**
 * Main application component with routing.
 */
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { isAuthenticated } from '@/services/api'
import ErrorBoundary from '@/components/ErrorBoundary'
import Login from '@/pages/Login'
import ChatbotList from '@/pages/admin/ChatbotList'
import ChatbotCreate from '@/pages/admin/ChatbotCreate'
import ChatbotDetail from '@/pages/admin/ChatbotDetail'
import ChatbotStats from '@/pages/admin/ChatbotStats'
import ChatPage from '@/pages/chat/ChatPage'
import Settings from '@/pages/admin/Settings'

// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

/**
 * Protected route wrapper - requires authentication.
 */
function ProtectedRoute() {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

/**
 * Public route wrapper - redirects if authenticated.
 */
function PublicRoute() {
  if (isAuthenticated()) {
    return <Navigate to="/admin" replace />
  }
  return <Outlet />
}

const NotFound = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="card max-w-md text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
      <p className="text-gray-600 mb-6">Page not found</p>
      <a href="/" className="btn-primary inline-block">
        Go Home
      </a>
    </div>
  </div>
)

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
          {/* Public routes (redirect if authenticated) */}
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<Login />} />
          </Route>

          {/* Protected admin routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/admin" element={<Navigate to="/admin/chatbots" replace />} />
            <Route path="/admin/chatbots" element={<ChatbotList />} />
            <Route path="/admin/chatbots/new" element={<ChatbotCreate />} />
            <Route path="/admin/chatbots/:id" element={<ChatbotDetail />} />
            <Route path="/admin/chatbots/:id/stats" element={<ChatbotStats />} />
            <Route path="/admin/settings" element={<Settings />} />
          </Route>

          {/* Public chat routes (no auth required) */}
          <Route path="/chat/:accessUrl" element={<ChatPage />} />

          {/* Default redirects */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
