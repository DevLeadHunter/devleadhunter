/**
 * Authentication middleware
 * Protects routes that require authentication
 * @module middleware/auth
 */

export default defineNuxtRouteMiddleware(async () => {
  /**
   * User store
   */
  const userStore = useUserStore()

  /**
   * Check if we're on client side
   */
  if (import.meta.client) {
    /**
     * First, initialize auth from localStorage if not already done
     * This ensures the store has the token before validation
     */
    if (!userStore.isAuthenticated) {
      userStore.initializeAuth()
    }

    /**
     * Validate authentication by calling /me endpoint
     * This ensures the token is still valid and updates user data
     */
    const isValid = await userStore.validateAuth()

    if (!isValid) {
      return navigateTo('/login')
    }
  } else {
    /**
     * On server side, we can't access localStorage
     * Allow navigation to happen, validation will occur on client side
     * This prevents false redirects in SSR
     */
    // Do nothing on SSR, let client handle validation
  }
})
