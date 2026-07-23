/**
 * Admin middleware
 * Protects routes that require admin role
 * @module middleware/admin
 */

export default defineNuxtRouteMiddleware(async () => {
  /**
   * User store
   */
  const userStore: ReturnType<typeof useUserStore> = useUserStore()

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

    /**
     * Check if user is admin (only after validation)
     * validateAuth() has updated userStore.user with fresh data from server
     */
    if (userStore.user?.role !== 'ADMIN') {
      return navigateTo('/dashboard')
    }
  } else {
    /**
     * On server side, we can't access localStorage or validate
     * Allow navigation to happen, validation will occur on client side
     * Don't check role on SSR as user data is not available
     */
    // Do nothing on SSR, let client handle validation and role check
  }
})
