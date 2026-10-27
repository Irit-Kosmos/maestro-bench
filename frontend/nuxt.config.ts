// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import { fileURLToPath } from 'node:url'
import { sharedRoutePath, unscopedRoutePath } from './app/utils/workspacePath'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      title: 'MAESTRO-bench',
      htmlAttrs: { lang: 'en' },
      link: [
        { rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
        { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
      ],
      meta: [
        { name: 'theme-color', content: '#000000' },
      ],
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
      // The "Source code" link of the help menu; override with NUXT_PUBLIC_SOURCE_URL, empty hides it
      SOURCE_URL: 'https://gitlab.irit.fr/talent/TALENT/around-elaastic/around-konsolidation/maestro-bench',
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
