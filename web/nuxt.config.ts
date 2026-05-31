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
      path: '~/components',
      pathPrefix: false,
      ignore: ['**/ui/**', '**/demo-sites/**'],
    },
  ],
  devtools: { enabled: !isDesktopBuild },

  app: {
    head: {
      title: 'DevLeadHunter — Find clients for your freelance business',
      htmlAttrs: {
        lang: 'en',
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1.0, user-scalable=no' },
        {
          name: 'description',
          content:
            'Smart prospecting tool for freelance web developers. Find businesses without websites and run personalized email campaigns.',
        },
        {
          name: 'keywords',
          content:
            'prospecting, freelance, web developer, client search, email marketing, campaigns, prospects, devleadhunter',
        },
        { name: 'author', content: 'DevLeadHunter' },
        { name: 'robots', content: 'index, follow' },
        { name: 'googlebot', content: 'index, follow' },
        { property: 'og:site_name', content: 'DevLeadHunter' },
        { property: 'og:locale', content: 'en_US' },
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
      githubRepo: process.env.NUXT_PUBLIC_GITHUB_REPO || 'leogu/devleadhunter',
      desktopReleaseChannel: process.env.NUXT_PUBLIC_DESKTOP_RELEASE_CHANNEL || 'latest',
      githubApiBase: process.env.NUXT_PUBLIC_GITHUB_API_BASE || 'https://api.github.com',
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
    locales: [
      { code: 'en', iso: 'en-US', name: 'English', file: 'en.json' },
      { code: 'fr', iso: 'fr-FR', name: 'Français', file: 'fr.json' },
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
