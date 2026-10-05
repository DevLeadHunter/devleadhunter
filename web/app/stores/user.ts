import type { TokenResponse } from '~/types/index'
import { defineStore } from 'pinia'
import type { User, LoginCredentials, SignupPayload, ProfileUpdate } from '~/types'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed } from 'vue'
import { AuthService, TokenRejectedError } from '~/services/authService'

/** Pinia store for auth session, profile and onboarding flag. */
// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useUserStore = defineStore('user', () => {
  // State
  const user: Ref<User | null> = ref(null)
  const token: Ref<string | null> = ref(null)
  const isLoading: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)
  const lastValidationTime: Ref<number | null> = ref(null)

  // Cache validation for 30 seconds to avoid excessive API calls
  const VALIDATION_CACHE_TIME: number = 30000

  // An app left open (the desktop app in the tray, the app installed on the iPad) trades its token
  // for a fresh one twice a day, so it never reaches the token's expiry while it is used.
  const TOKEN_RENEWAL_INTERVAL_MS: number = 12 * 60 * 60 * 1000
  const TOKEN_RENEWED_AT_KEY: string = 'token_renewed_at'
  let isRenewingToken: boolean = false

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
      const tokenResponse: TokenResponse = await AuthService.login(credentials)
      token.value = tokenResponse.access_token

      // Get user information
      const userData: User = await AuthService.getCurrentUser(token.value)
      user.value = userData

      // Store token and user in localStorage
      if (import.meta.client) {
        localStorage.setItem('token', token.value)
        localStorage.setItem('user', JSON.stringify(user.value))
        localStorage.setItem(TOKEN_RENEWED_AT_KEY, String(Date.now()))
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
      const userData: User = await AuthService.signup(data)
      user.value = userData

      // Login the new user
      const tokenResponse: TokenResponse = await AuthService.login({
        email: data.email,
        password: data.password,
      })
      token.value = tokenResponse.access_token

      // Store token and user in localStorage
      if (import.meta.client) {
        localStorage.setItem('token', token.value)
        localStorage.setItem('user', JSON.stringify(user.value))
        localStorage.setItem(TOKEN_RENEWED_AT_KEY, String(Date.now()))
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
    localStorage.removeItem(TOKEN_RENEWED_AT_KEY)
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
        const storedToken: string | null = localStorage.getItem('token')
        const storedUser: string | null = localStorage.getItem('user')

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

    const storedToken: string | null = localStorage.getItem('token')

    if (!storedToken) {
      token.value = null
      user.value = null
      lastValidationTime.value = null
      return false
    }

    // Check if we have a recent validation (within cache time)
    const now: number = Date.now()
    if (lastValidationTime.value && now - lastValidationTime.value < VALIDATION_CACHE_TIME) {
      // Return cached authentication status
      return token.value !== null && user.value !== null
    }

    try {
      // Set token first so API call can use it
      token.value = storedToken

      // Call /me to validate token and get current user data
      const userData: User = await AuthService.getCurrentUser(storedToken)

      // Update user with fresh data from server
      user.value = userData

      // Update localStorage with fresh user data
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('token', storedToken)

      // Update validation cache time
      lastValidationTime.value = now

      void renewTokenIfAging()
      return true
    } catch (error) {
      // The API out of reach (no network yet when Windows starts the desktop app, a restart) says
      // nothing about the token: the session read from this device stays, the next check confirms it.
      const storedUser: string | null = localStorage.getItem('user')
      if (!(error instanceof TokenRejectedError) && storedUser) {
        user.value = user.value ?? JSON.parse(storedUser)
        return true
      }
      // Token is invalid or expired, clear auth
      console.error('Auth validation failed:', error)
      token.value = null
      user.value = null
      lastValidationTime.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem(TOKEN_RENEWED_AT_KEY)
      return false
    }
  }

  /**
   * Trade the token for a fresh one when it was last renewed more than half a day ago.
   * @returns A promise resolved once the token is renewed, or was recent enough.
   */
  async function renewTokenIfAging(): Promise<void> {
    if (!import.meta.client || !token.value || isRenewingToken) return
    const renewedAt: number = Number(localStorage.getItem(TOKEN_RENEWED_AT_KEY) ?? 0)
    if (Date.now() - renewedAt < TOKEN_RENEWAL_INTERVAL_MS) return
    const renewedToken: string = token.value
    isRenewingToken = true
    try {
      const renewal: TokenResponse = await AuthService.refreshToken(renewedToken)
      // A sign-out or another account while the request ran: the answer belongs to nobody now.
      if (token.value !== renewedToken) return
      token.value = renewal.access_token
      localStorage.setItem('token', renewal.access_token)
      localStorage.setItem(TOKEN_RENEWED_AT_KEY, String(Date.now()))
    } catch {
      // Tried again at the next check; a token the API refuses is handled by validateAuth.
    } finally {
      isRenewingToken = false
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

    const storedToken: string | null = localStorage.getItem('token')

    if (!storedToken) {
      return
    }

    try {
      // Force refresh by resetting cache
      lastValidationTime.value = null
      token.value = storedToken

      // Call /me to get fresh user data from server
      const userData: User = await AuthService.getCurrentUser(storedToken)

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
    renewTokenIfAging,
    refreshUser,
  }
})
