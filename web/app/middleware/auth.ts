/**
 * Authentication middleware
 * Protects routes that require authentication
 * @module middleware/auth
 */

/** Where a user who has not finished the setup wizard is nudged to. */
const SETUP_ROUTE = '/configuration'

export default defineNuxtRouteMiddleware(async (to) => {
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

    /**
     * Fresh accounts land on the setup wizard until they finish it — unless they
     * explicitly chose to configure later. The query is carried over so an OAuth
     * redirect (e.g. `?gmail=connected`) is still surfaced on the wizard.
     */
    const { isPostponed } = useOnboarding()
    const needsSetup = userStore.user?.onboarding_completed === false && !isPostponed()

    if (needsSetup && to.path !== SETUP_ROUTE && to.path.startsWith('/dashboard')) {
      return navigateTo({ path: SETUP_ROUTE, query: to.query })
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
