/**
 * Authentication state hook.
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { isAuthenticated, removeAccessToken } from '@/services/api'
import {
  login as loginApi,
  getCurrentUser,
  LoginRequest,
  AdminUser,
} from '@/services/auth'

interface UseAuthReturn {
  user: AdminUser | null
  isLoading: boolean
  isAuthenticated: boolean
  error: Error | null
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
}

/**
 * Hook for authentication state management.
 */
export function useAuth(): UseAuthReturn {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<Error | null>(null)

  // Query for current user
  const {
    data: user,
    isLoading,
    error: queryError,
  } = useQuery({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
    enabled: isAuthenticated(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: loginApi,
    onSuccess: () => {
      // Refetch user data after login
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
      navigate('/admin')
    },
    onError: (err: Error) => {
      setError(err)
    },
  })

  // Login handler
  const login = useCallback(
    async (credentials: LoginRequest) => {
      setError(null)
      await loginMutation.mutateAsync(credentials)
    },
    [loginMutation]
  )

  // Logout handler
  const logout = useCallback(() => {
    removeAccessToken()
    queryClient.clear()
    navigate('/login')
  }, [navigate, queryClient])

  // Set error from query
  useEffect(() => {
    if (queryError) {
      setError(queryError as Error)
    }
  }, [queryError])

  return {
    user: user ?? null,
    isLoading: isLoading || loginMutation.isPending,
    isAuthenticated: !!user,
    error,
    login,
    logout,
  }
}

/**
 * Hook to require authentication.
 * Redirects to login if not authenticated.
 */
export function useRequireAuth(): { user: AdminUser | null; isLoading: boolean } {
  const navigate = useNavigate()
  const { user, isLoading, isAuthenticated: authenticated } = useAuth()

  useEffect(() => {
    if (!isLoading && !authenticated) {
      navigate('/login', { replace: true })
    }
  }, [isLoading, authenticated, navigate])

  return { user, isLoading }
}
