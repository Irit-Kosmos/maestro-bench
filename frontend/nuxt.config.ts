import { fileURLToPath } from 'node:url'
import { sharedRoutePath, unscopedRoutePath } from './app/utils/workspacePath'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      title: 'MAESTRO-bench',
      htmlAttrs: { lang: 'en' },
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
      { name: 'Geist', provider: 'google', weights: [400, 500, 600, 700] },
    ],
  },

  // Logos missing from the logos set live in app/assets/icons: i-custom-<file name>
  icon: {
    customCollections: [
      { prefix: 'custom', dir: './app/assets/icons' },
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

  hooks: {
    // Links and shortcuts name a page without its workspace (`/experiments/3`) and the auth middleware
    // sends them to `/w/<slug>/...`. Without a route for these paths, the router warns on every one.
    // (An alias cannot do it: it must have the same params as its page, `slug` included.)
    'pages:extend': (pages) => {
      const file = fileURLToPath(new URL('./app/components/App/Redirecting.vue', import.meta.url))
      const unscoped = pages.flatMap((page) => {
        const path = unscopedRoutePath(page.path)
        return path ? [{ path, file }] : []
      })
      pages.push(...unscoped)

      // The pages a public link opens are the app's own, served again behind the link (`/s/<token>/...`)
      const shared = pages.flatMap((page) => {
        const path = sharedRoutePath(page.path)
        return path && page.file ? [{ path, file: page.file }] : []
      })
      pages.push(...shared)
    },
  },
})
