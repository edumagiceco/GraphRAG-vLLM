/**
 * Authentication API service.
 */
import { api, setAccessToken, removeAccessToken } from './api'

// Types
export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface AdminUser {
  id: string
  email: string
  created_at: string
}

/**
 * Login with email and password.
 */
export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>('/auth/login', credentials)
  const data = response.data

  // Store token
  setAccessToken(data.access_token)

  return data
}

/**
 * Logout user.
 */
export function logout(): void {
  removeAccessToken()
  window.location.href = '/login'
}

/**
 * Get current user information.
 */
export async function getCurrentUser(): Promise<AdminUser> {
  const response = await api.get<AdminUser>('/auth/me')
  return response.data
}
