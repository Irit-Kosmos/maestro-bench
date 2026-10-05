const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

export default defineNuxtPlugin({
  setup(nuxtApp) {
    const { csrfToken, forget } = useAuth()

    const api = $fetch.create({
      baseURL: `${useRuntimeConfig().public.BACK_URL}/`,
      // The session cookie is HttpOnly and belongs to the API's origin
      credentials: 'include',
      onRequest({ options }) {
        if (SAFE_METHODS.includes((options.method ?? 'GET').toUpperCase()) || !csrfToken.value)
          return
        const headers = new Headers(options.headers)
        headers.set('X-CSRF-Token', csrfToken.value)
        options.headers = headers
      },
      onResponseError({ response }) {
        // The session ended (expired, signed out elsewhere, user deactivated): sign in again
        if (response.status !== 401)
          return
        forget()
        nuxtApp.runWithContext(() => {
          const route = useRoute()
          if (route.path !== '/login')
            return navigateTo({ path: '/login', query: { next: route.fullPath } })
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
