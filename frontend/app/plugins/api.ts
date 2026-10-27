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

const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

export default defineNuxtPlugin({
  setup(nuxtApp) {
    const { csrfToken, forget } = useAuth()
    const router = useRouter()

    // Whatever the app creates or deletes can tick a step of the getting-started list: look again, once
    let refreshSetup: ReturnType<typeof setTimeout> | undefined

    const api = $fetch.create({
      baseURL: `${useRuntimeConfig().public.BACK_URL}/`,
      // The session cookie is HttpOnly and belongs to the API's origin
      credentials: 'include',
      onRequest(context) {
        // What the app holds lives in the workspace of the URL, or behind the public link of the page:
        // callers say `/experiments`
        const { request, options } = context
        const pagePath = router.currentRoute.value.path
        if (typeof request === 'string' && isWorkspaceApiPath(request)) {
          const scoped = scopeApiPath(request, pagePath)
          if (!scoped)
            throw new Error(`No workspace selected for ${request}`)
          context.request = scoped
        }
        // A public link is read without an account: the session of whoever opens it is none of its business
        if (shareOfPath(pagePath))
          options.credentials = 'omit'

        if (SAFE_METHODS.includes((options.method ?? 'GET').toUpperCase()) || !csrfToken.value)
          return
        const headers = new Headers(options.headers)
        headers.set('X-CSRF-Token', csrfToken.value)
        options.headers = headers
      },
      onResponse({ options }) {
        if (SAFE_METHODS.includes((options.method ?? 'GET').toUpperCase()))
          return
        clearTimeout(refreshSetup)
        refreshSetup = setTimeout(() => nuxtApp.runWithContext(() => refreshNuxtData('setup-progress')), 300)
      },
      onResponseError({ response }) {
        // The session ended (expired, signed out elsewhere, user deactivated): sign in again
        if (response.status !== 401 || shareOfPath(router.currentRoute.value.path))
          return
        forget()
        nuxtApp.runWithContext(() => {
          const route = useRoute()
          if (route.path !== '/login')
            return navigateTo({ path: '/login', query: { next: route.fullPath, error: 'session_expired' } })
        })
      },
    })

    return {
      provide: {
        api,
      },
    }
  },
})
