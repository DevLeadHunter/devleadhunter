// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from 'nuxt/config'

const isDesktopBuild: boolean = process.env.NUXT_DESKTOP_BUILD === '1'

export default defineNuxtConfig({
  modules: ['@nuxt/eslint', '@nuxt/ui', '@vueuse/nuxt', '@pinia/nuxt', '@nuxtjs/i18n'],

  ssr: !isDesktopBuild,

  components: [
    {
      path: '~/components/ui',
      prefix: 'Ui',
    },
    {
      path: '~/components/demo-sites',
      prefix: 'DemoSites',
    },
    {
      path: '~/components/dashboard',
      prefix: 'Dashboard',
    },
    {
      path: '~/components',
      pathPrefix: false,
      ignore: ['**/ui/**', '**/demo-sites/**', '**/dashboard/**'],
    },
  ],
  devtools: { enabled: !isDesktopBuild },

  app: {
    head: {
      title: 'DevLeadHunter — Turn businesses without a website into paying clients',
      htmlAttrs: {
        lang: 'en',
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'DevLeadHunter finds local businesses without a website, automatically generates a demo site for each, reaches out by cold email and deploys their site live when they pay. End-to-end prospecting automation on web, desktop and mobile.',
        },
        {
          name: 'keywords',
          content:
            'prospecting automation, freelance web developer, lead generation, cold email, demo website generation, businesses without websites, devleadhunter',
        },
        { name: 'author', content: 'DevLeadHunter' },
        { name: 'robots', content: 'index, follow' },
        { name: 'googlebot', content: 'index, follow' },
        { property: 'og:site_name', content: 'DevLeadHunter' },
        { property: 'og:locale', content: 'en_US' },
        // Social preview card (generated in the landing "Atelier" DA)
        { property: 'og:image', content: 'https://devleadhunter.dibodev.fr/og-image.png' },
        { property: 'og:image:width', content: '1200' },
        { property: 'og:image:height', content: '630' },
        { property: 'og:image:type', content: 'image/png' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:image', content: 'https://devleadhunter.dibodev.fr/og-image.png' },
        { name: 'twitter:site', content: '@devleadhunter' },
        { name: 'theme-color', content: '#050505' },
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
        },
        // Landing fonts (editorial redesign) — loaded from the Google Fonts CDN for the
        // same reason as Inter above (self-hosted fonts broken on the OVH/nginx host).
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,500;1,9..144,600&family=Instrument+Sans:ital,wght@0,400;0,500;0,600;1,400&family=Spline+Sans+Mono:wght@400;500&display=swap',
        },
        // App (dashboard) fonts — IBM Plex, a software-grade family distinct
        // from the marketing site typography.
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap',
        },
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
      ],
      script: [
        ...(isDesktopBuild
          ? []
          : [
              {
                src: 'https://www.umami.dibodev.fr/script.js',
                defer: true,
                'data-website-id': '0734f93b-7047-425b-8593-1f5b2711c6ff',
              },
            ]),
      ],
    },
  },

  css: ['~/assets/css/main.css'],

  colorMode: {
    preference: 'dark',
    fallback: 'dark',
    classSuffix: '',
  },

  ui: {
    // Disable @nuxt/ui's bundled @nuxt/fonts self-hosting. On the OVH/nginx host the
    // self-hosted /_fonts/*.woff2 are served with the wrong MIME type (application/json)
    // and, with nosniff, the browser aborts the download. Inter is loaded from the Google
    // Fonts CDN <link> in app.head instead, which serves the correct font/woff2 MIME.
    fonts: false,
    theme: {
      colors: ['primary', 'neutral', 'success', 'info', 'warning', 'error'],
    },
  },

  runtimeConfig: {
    public: {
      apiBase:
        process.env.NUXT_PUBLIC_API_BASE ||
        process.env.API_BASE_URL ||
        (process.env.NODE_ENV === 'production' ? 'https://api.devleadhunter.dibodev.fr' : 'http://localhost:8000'),
      githubRepo: process.env.NUXT_PUBLIC_GITHUB_REPO || 'DevLeadHunter/devleadhunter',
      desktopReleaseChannel: process.env.NUXT_PUBLIC_DESKTOP_RELEASE_CHANNEL || 'latest',
      githubApiBase: process.env.NUXT_PUBLIC_GITHUB_API_BASE || 'https://api.github.com',
      // Base URL of the demo-host app — used to iframe live template previews in the builder.
      demoHostBase:
        process.env.NUXT_PUBLIC_DEMO_HOST_BASE ||
        (process.env.NODE_ENV === 'production' ? 'https://demo.dibodev.fr' : 'http://localhost:3001'),
      // True for the Tauri desktop build → the landing page redirects to the app.
      isDesktop: isDesktopBuild,
      // PostHog — marketing-site tracking (surface: 'marketing'). Same project as the
      // demo sites; empty key → tracking disabled. Only the public site is tracked,
      // never the dashboard app (see plugins/posthog.client.ts).
      posthogProjectApiKey: process.env.NUXT_PUBLIC_POSTHOG_PROJECT_API_KEY || '',
      posthogIngestionHost: process.env.NUXT_PUBLIC_POSTHOG_INGESTION_HOST || 'https://eu.i.posthog.com',
    },
  },

  compatibilityDate: '2024-07-11',

  nitro: isDesktopBuild
    ? {
        preset: 'static',
      }
    : undefined,

  typescript: {
    strict: true,
    typeCheck: false,
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'only-multiline',
        braceStyle: '1tbs',
      },
    },
  },

  i18n: {
    // Absolute base for hreflang/og:locale alternate links (SEO).
    baseUrl: 'https://devleadhunter.dibodev.fr',
    locales: [
      { code: 'en', language: 'en-US', name: 'English', file: 'en.json' },
      { code: 'fr', language: 'fr-FR', name: 'Français', file: 'fr.json' },
    ],
    defaultLocale: 'en',
    strategy: 'prefix_except_default',
    langDir: 'locales',
    vueI18n: 'i18n.config.ts',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root',
    },
  },
})
