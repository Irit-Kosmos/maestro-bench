// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      title: 'MAESTRO-bench',
    },
    pageTransition: { name: 'page', mode: 'out-in' },
  },
  devtools: { enabled: true },

  modules: [
    '@nuxt/ui',
    '@nuxt/eslint',
    '@nuxt/icon',
    '@nuxt/fonts',
    '@vueuse/nuxt',
  ],

  fonts: {
    families: [
      { name: 'Instrument Sans', provider: 'google', weights: [400, 500, 600, 700] },
      { name: 'Space Grotesk', provider: 'google', weights: [400, 500, 600, 700] },
    ],
  },

  css: ['~/assets/css/main.css'],

  future: {
    compatibilityVersion: 4,
  },

  compatibilityDate: '2024-11-27',

  ui: {
    colorMode: false,
  },

  runtimeConfig: {
    public: {
      BACK_URL: '',
    },
  },

  ssr: false,
})
