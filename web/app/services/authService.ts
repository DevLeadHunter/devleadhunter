import type { User, LoginCredentials, SignupData, TokenResponse } from '~/types'

/**
 * Authentication service for user management
 * @module services/authService
 */

/**
 * Get API base URL
 * @returns {string} The API base URL
 */
function getApiUrl(): string {
  const config = useRuntimeConfig()
  return config.public.apiBase
}

/**
 * Login user
 * @param {LoginCredentials} credentials - Login credentials
 * @returns {Promise<TokenResponse>} Token response
 * @throws {Error} If login fails
 */
export async function login(credentials: LoginCredentials): Promise<TokenResponse> {
  const response = await fetch(`${getApiUrl()}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

/**
 * Signup new user
 * @param {SignupData} data - Signup data
 * @returns {Promise<User>} Created user
 * @throws {Error} If signup fails
 */
export async function signup(data: SignupData): Promise<User> {
  const response = await fetch(`${getApiUrl()}/api/v1/auth/signup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Signup failed' }))
    throw new Error(error.detail || 'Signup failed')
  }

  return response.json()
}

/**
 * Get current user information
 * @param {string} token - JWT token
 * @returns {Promise<User>} Current user
 * @throws {Error} If request fails
 */
export async function getCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${getApiUrl()}/api/v1/auth/me`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error('Failed to get current user')
  }

  return response.json()
}
