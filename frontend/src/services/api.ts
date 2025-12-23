/**
 * Axios API client with authentication interceptor.
 */
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Token storage keys
const ACCESS_TOKEN_KEY = 'graphrag_access_token'

/**
 * Get stored access token.
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

/**
 * Store access token.
 */
export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

/**
 * Remove stored access token.
 */
export function removeAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

/**
 * Check if user is authenticated.
 */
export function isAuthenticated(): boolean {
  return !!getAccessToken()
}

/**
 * Create configured axios instance.
 */
function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Request interceptor - add auth token
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = getAccessToken()
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error: AxiosError) => {
      return Promise.reject(error)
    }
  )

  // Response interceptor - handle auth errors
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      // Handle both 401 (Unauthorized) and 403 (Forbidden/Not authenticated)
      if (error.response?.status === 401 || error.response?.status === 403) {
        // Token expired, invalid, or missing
        removeAccessToken()
        // Redirect to login if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      return Promise.reject(error)
    }
  )

  return client
}

// Export configured API client
export const api = createApiClient()

// Default export for convenience
export default api

// Export types
export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export function isApiError(error: unknown): error is AxiosError<ApiError> {
  return axios.isAxiosError(error)
}

export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    // FastAPI returns 'detail', but also check 'message' for compatibility
    const data = error.response?.data as { detail?: string; message?: string } | undefined
    return data?.detail || data?.message || error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unknown error occurred'
}
