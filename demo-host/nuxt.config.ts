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
          href: 'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800;900&family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700;12..96,800&family=Chakra+Petch:wght@400;500;600;700&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap',
        },
      ],
    },
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      // PostHog (behavioural tracking on demo sites). Empty key → tracking disabled.
      // Project API Key (phc_, publique) + host d'ingestion.
      posthogProjectApiKey: process.env.NUXT_PUBLIC_POSTHOG_PROJECT_API_KEY || '',
      posthogIngestionHost: process.env.NUXT_PUBLIC_POSTHOG_INGESTION_HOST || 'https://eu.i.posthog.com',
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
