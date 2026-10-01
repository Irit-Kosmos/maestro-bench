// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      title: 'MAESTRO-bench',
    },
  },
  devtools: { enabled: true },

  modules: [
    '@nuxt/ui',
    '@nuxt/icon',
    '@nuxt/fonts',
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

  // Follows the OS until the user picks a side; the choice persists in localStorage
  colorMode: {
    preference: 'system',
    fallback: 'light',
    storageKey: 'maestro-color-mode',
  },

  runtimeConfig: {
    public: {
      // Override with NUXT_PUBLIC_BACK_URL
      BACK_URL: 'http://localhost:8000',
    },
  },

  ssr: false,
})
