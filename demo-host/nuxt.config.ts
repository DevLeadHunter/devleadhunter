import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  ssr: true,
  modules: ['@nuxt/eslint'],

  // Website templates consumed as Nuxt layers from GitHub (public repos, no token),
  // pinned by tag. Each exposes one root component + relative-only sections.
  extends: [
    'github:DevLeadHunter/devleadhunter-template-artisan-edito#v1.3.1',
    'github:DevLeadHunter/devleadhunter-template-plumber-signature#v1.3.1',
    'github:DevLeadHunter/devleadhunter-template-plumber-atelier#v1.4.1',
    'github:DevLeadHunter/devleadhunter-template-plumber-cuivre#v1.3.1',
    'github:DevLeadHunter/devleadhunter-template-electrician-lumen#v1.3.1',
    'github:DevLeadHunter/devleadhunter-template-mechanic-pitlane#v1.3.8',
    'github:DevLeadHunter/devleadhunter-template-dental#v1.2.3',
    'github:DevLeadHunter/devleadhunter-template-food#v1.1.6',
    'github:DevLeadHunter/devleadhunter-template-barber#v1.2.7',
    'github:DevLeadHunter/devleadhunter-template-landscaper-verdure#v1.5.0',
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
      // Public project key (phc_); ingestion goes through the first-party proxy
      // (server/routes/dibodev/events), so no ingestion host is configured client-side.
      posthogProjectApiKey: process.env.NUXT_PUBLIC_POSTHOG_PROJECT_API_KEY || '',
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
          'https://devleadhunter.fr https://devleadhunter.dibodev.fr http://localhost:3000 http://localhost:1420 ' +
          'http://tauri.localhost https://tauri.localhost',
      },
    },
  },
})
