import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  ssr: true,

  // Website templates consumed as Nuxt layers from GitHub (public repos, no token),
  // pinned by tag. Each exposes one root component + relative-only sections.
  extends: [
    'github:DevLeadHunter/devleadhunter-template-artisan-edito#v1.2.0',
    'github:DevLeadHunter/devleadhunter-template-plumber-signature#v1.2.0',
    'github:DevLeadHunter/devleadhunter-template-plumber-atelier#v1.3.0',
    'github:DevLeadHunter/devleadhunter-template-plumber-cuivre#v1.2.0',
    'github:DevLeadHunter/devleadhunter-template-electrician-lumen#v1.2.0',
  ],

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
        // No global font stylesheet: each template layer declares its own fonts (root `useHead`).
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
        // Allow embedding in the Storyblok Visual Editor AND the DevLeadHunter dashboard
        // (web + Tauri desktop) so the builder can iframe live template previews.
        'Content-Security-Policy':
          "frame-ancestors 'self' https://app.storyblok.com https://*.storyblok.com " +
          'https://devleadhunter.dibodev.fr http://localhost:3000 http://localhost:1420 ' +
          'http://tauri.localhost https://tauri.localhost',
      },
    },
  },
})
