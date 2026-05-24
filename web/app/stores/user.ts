import { defineStore } from 'pinia'
import type { User, LoginCredentials, SignupData } from '~/types'
import type { Ref } from 'vue'
import { ref, computed } from 'vue'
import * as authService from '~/services/authService'

/**
 * Pinia store for user authentication and profile management
 * @module stores/user
 */

/**
 * User store definition
 */
export const useUserStore = defineStore('user', () => {
  // State
  const user: Ref<User | null> = ref(null)
  const token: Ref<string | null> = ref(null)
  const isLoading: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)
  const lastValidationTime: Ref<number | null> = ref(null)

  // Cache validation for 30 seconds to avoid excessive API calls
  const VALIDATION_CACHE_TIME = 30000

  // Getters
  const isAuthenticated = computed(() => {
    return user.value !== null && token.value !== null
  })

  const userName = computed(() => {
    return user.value?.name ?? ''
  })

  const userEmail = computed(() => {
    return user.value?.email ?? ''
  })

  /**
   * Login user with credentials
   * @param {LoginCredentials} credentials - Login credentials
   * @returns {Promise<void>} Promise that resolves when login is complete
   * @throws {Error} If login fails
   * @example
   * ```typescript
   * await userStore.login({ email: 'user@example.com', password: 'password' });
   * ```
   */
  async function login(credentials: LoginCredentials): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      // Call auth service
      const tokenResponse = await authService.login(credentials)
      token.value = tokenResponse.access_token

      // Get user information
      const userData = await authService.getCurrentUser(token.value)
      user.value = userData

      // Store token and user in localStorage
      if (import.meta.client) {
        localStorage.setItem('token', token.value)
        localStorage.setItem('user', JSON.stringify(user.value))
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Login failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Signup new user
   * @param {SignupData} data - Signup data
   * @returns {Promise<void>} Promise that resolves when signup is complete
   * @throws {Error} If signup fails
   * @example
   * ```typescript
   * await userStore.signup({
   *   name: 'John Doe',
   *   email: 'john@example.com',
   *   password: 'password'
   * });
   * ```
   */
  async function signup(data: SignupData): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      // Call auth service to create user
      const userData = await authService.signup(data)
      user.value = userData

      // Login the new user
      const tokenResponse = await authService.login({
        email: data.email,
        password: data.password,
      })
      token.value = tokenResponse.access_token

      // Store token and user in localStorage
      if (import.meta.client) {
        localStorage.setItem('token', token.value)
        localStorage.setItem('user', JSON.stringify(user.value))
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Signup failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Logout current user
   * @returns {void}
   */
  function logout(): void {
    user.value = null
    token.value = null
    lastValidationTime.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  /**
   * Update user profile
   * @param {Partial<User>} data - Updated user data
   * @returns {Promise<void>} Promise that resolves when update is complete
   * @throws {Error} If update fails
   */
  async function updateProfile(data: Partial<User>): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      // Mock API call - simulate network delay
      await new Promise((resolve) => setTimeout(resolve, 800))

      if (user.value) {
        user.value = { ...user.value, ...data }
        if (import.meta.client) {
          localStorage.setItem('user', JSON.stringify(user.value))
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Profile update failed'
      throw err
    } finally {
      isLoading.value = false
    }

    // TODO: Replace with actual API call
    // const response = await $fetch('/api/auth/profile', {
    //   method: 'PUT',
    //   headers: { Authorization: `Bearer ${token.value}` },
    //   body: data
    // });
  }

  /**
   * Initialize user from localStorage
   * @returns {void}
   */
  function initializeAuth(): void {
    if (import.meta.client) {
      try {
        const storedToken = localStorage.getItem('token')
        const storedUser = localStorage.getItem('user')

        if (storedToken && storedUser) {
          token.value = storedToken
          user.value = JSON.parse(storedUser)
        }
      } catch (error) {
        // If there's an error parsing user data, clear invalid data
        console.error('Error initializing auth from localStorage:', error)
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        token.value = null
        user.value = null
      }
    }
  }

  /**
   * Validate authentication by calling /me endpoint
   * Updates user data if token is valid, otherwise clears auth
   * Uses cache to avoid excessive API calls
   * @returns {Promise<boolean>} True if authenticated, false otherwise
   */
  async function validateAuth(): Promise<boolean> {
    if (typeof window === 'undefined') {
      return false
    }

    const storedToken = localStorage.getItem('token')

    if (!storedToken) {
      token.value = null
      user.value = null
      lastValidationTime.value = null
      return false
    }

    // Check if we have a recent validation (within cache time)
    const now = Date.now()
    if (lastValidationTime.value && now - lastValidationTime.value < VALIDATION_CACHE_TIME) {
      // Return cached authentication status
      return token.value !== null && user.value !== null
    }

    try {
      // Set token first so API call can use it
      token.value = storedToken

      // Call /me to validate token and get current user data
      const userData = await authService.getCurrentUser(storedToken)

      // Update user with fresh data from server
      user.value = userData

      // Update localStorage with fresh user data
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('token', storedToken)

      // Update validation cache time
      lastValidationTime.value = now

      return true
    } catch (error) {
      // Token is invalid or expired, clear auth
      console.error('Auth validation failed:', error)
      token.value = null
      user.value = null
      lastValidationTime.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      return false
    }
  }

  /**
   * Refresh user data from API, bypassing cache
   * Useful after operations that modify user data (e.g., credit purchase)
   * @returns {Promise<void>} Promise that resolves when refresh is complete
   * @throws {Error} If refresh fails
   */
  async function refreshUser(): Promise<void> {
    if (typeof window === 'undefined') {
      return
    }

    const storedToken = localStorage.getItem('token')

    if (!storedToken) {
      return
    }

    try {
      // Force refresh by resetting cache
      lastValidationTime.value = null
      token.value = storedToken

      // Call /me to get fresh user data from server
      const userData = await authService.getCurrentUser(storedToken)

      // Update user with fresh data from server
      user.value = userData

      // Update localStorage with fresh user data
      if (import.meta.client) {
        localStorage.setItem('user', JSON.stringify(userData))
        localStorage.setItem('token', storedToken)
      }

      // Update validation cache time
      lastValidationTime.value = Date.now()
    } catch (error) {
      console.error('Failed to refresh user data:', error)
      // Don't clear auth on refresh failure, just log error
    }
  }

  return {
    // State
    user,
    token,
    isLoading,
    error,
    // Getters
    isAuthenticated,
    userName,
    userEmail,
    // Actions
    login,
    signup,
    logout,
    updateProfile,
    initializeAuth,
    validateAuth,
    refreshUser,
  }
})
