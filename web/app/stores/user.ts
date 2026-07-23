import { defineStore } from 'pinia'
import type { User, LoginCredentials, SignupPayload, ProfileUpdate } from '~/types'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed } from 'vue'
import { AuthService } from '~/services/authService'

/** Pinia store for auth session, profile and onboarding flag. */
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
  const isAuthenticated: ComputedRef<boolean> = computed(() => {
    return user.value !== null && token.value !== null
  })

  const userName: ComputedRef<string> = computed(() => {
    return user.value?.name ?? ''
  })

  const userEmail: ComputedRef<string> = computed(() => {
    return user.value?.email ?? ''
  })

  /**
   * Login user with credentials
   * @param credentials - Login credentials
   * @returns Promise that resolves when login is complete
   * @throws If login fails
   */
  async function login(credentials: LoginCredentials): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      // Call auth service
      const tokenResponse = await AuthService.login(credentials)
      token.value = tokenResponse.access_token

      // Get user information
      const userData = await AuthService.getCurrentUser(token.value)
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
   * @param data - Signup data
   * @returns Promise that resolves when signup is complete
   * @throws If signup fails
   */
  async function signup(data: SignupPayload): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      // Call auth service to create user
      const userData = await AuthService.signup(data)
      user.value = userData

      // Login the new user
      const tokenResponse = await AuthService.login({
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
   */
  function logout(): void {
    user.value = null
    token.value = null
    lastValidationTime.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  /**
   * Update the current user's profile (name/email) server-side and sync local state.
   * @param data - Fields to update (name and/or email).
   * @returns Promise that resolves when the update is persisted.
   * @throws If not authenticated or the update fails (e.g. email taken).
   */
  async function updateProfile(data: ProfileUpdate): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      if (!token.value) {
        throw new Error('Not authenticated')
      }

      // Persist to the API — the server is the source of truth for the returned user.
      const updatedUser: User = await AuthService.updateProfile(token.value, data)
      user.value = updatedUser

      if (import.meta.client) {
        localStorage.setItem('user', JSON.stringify(updatedUser))
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Profile update failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Mark the post-signup setup wizard as completed and sync local state.
   * @returns Promise that resolves once the flag is persisted.
   * @throws If not authenticated or the request fails.
   */
  async function completeOnboarding(): Promise<void> {
    if (!token.value) {
      throw new Error('Not authenticated')
    }

    const updatedUser: User = await AuthService.completeOnboarding(token.value)
    user.value = updatedUser

    if (import.meta.client) {
      localStorage.setItem('user', JSON.stringify(updatedUser))
    }
  }

  /**
   * Initialize user from localStorage
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
   * @returns True if authenticated, false otherwise
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
      const userData = await AuthService.getCurrentUser(storedToken)

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
   * @returns Promise that resolves when refresh is complete
   * @throws If refresh fails
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
      const userData = await AuthService.getCurrentUser(storedToken)

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
    completeOnboarding,
    initializeAuth,
    validateAuth,
    refreshUser,
  }
})
