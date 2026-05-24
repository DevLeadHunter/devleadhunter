export default defineNuxtConfig({
  ssr: true,
  compatibilityDate: '2024-07-11',
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
    },
  },
  routeRules: {
    '/**': { cors: true },
  },
})
