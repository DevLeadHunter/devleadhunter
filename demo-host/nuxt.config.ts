import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  ssr: true,
  compatibilityDate: '2024-07-11',
  css: ['~/assets/css/main.css'],
  vite: {
    plugins: [tailwindcss()],
  },
  app: {
    head: {
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap',
        },
      ],
    },
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
    },
  },
  routeRules: {
    '/**': {
      cors: true,
      headers: {
        'Content-Security-Policy': "frame-ancestors 'self' https://app.storyblok.com https://*.storyblok.com",
      },
    },
  },
})
