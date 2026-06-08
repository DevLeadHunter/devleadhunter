/**
 * On the Tauri desktop build, the marketing landing page is skipped: the app
 * goes straight to the dashboard (the global auth middleware then bounces to
 * /login when the user is not authenticated). On the web build this is a no-op,
 * so the public landing page is preserved.
 */
export default defineNuxtRouteMiddleware((): ReturnType<typeof navigateTo> | undefined => {
  const config = useRuntimeConfig()
  if (config.public.isDesktop) {
    return navigateTo('/dashboard', { replace: true })
  }
  return undefined
})
