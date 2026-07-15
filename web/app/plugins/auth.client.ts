/**
 * Authentication plugin to initialize user store on app startup
 * This runs only on client-side
 */
export default defineNuxtPlugin(() => {
  const userStore = useUserStore()

  // Initialize auth from localStorage (always client-side in .client.ts plugin)
  userStore.initializeAuth()
})
