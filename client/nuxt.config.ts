// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  
  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt'
  ],
  
  css: ['~/assets/css/main.css'],
  
  app: {
    head: {
      title: 'devleadhunter',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1.0, user-scalable=no' },
        { name: 'description', content: 'devleadhunter - Personal prospect research tool for freelance web developers' }
      ],
      link: [
        {
          rel: 'preconnect',
          href: 'https://fonts.googleapis.com'
        },
        {
          rel: 'preconnect',
          href: 'https://fonts.gstatic.com',
          crossorigin: ''
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        },
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
      ],
      script: [
        {
          src: 'https://kit.fontawesome.com/dcc05147de.js',
          crossorigin: 'anonymous'
        }
      ]
    }
  },
  
  typescript: {
    strict: true,
    typeCheck: false
  },
  
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || (process.env.NODE_ENV === 'production' 
        ? 'https://api.devleadhunter.dibodev.fr' 
        : 'http://localhost:8000')
    }
  },
  
})

