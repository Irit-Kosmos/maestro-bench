import type { AuthUser } from '~/types'

interface Me {
  user: AuthUser
  csrf_token: string
}

/**
 * Who is signed in. The session lives in an HttpOnly cookie the page can't read:
 * `/auth/me` is how it learns who it is and which CSRF token to send with writes.
 */
export function useAuth() {
  const user = useState<AuthUser | null>('auth-user', () => null)
  const csrfToken = useState<string | null>('auth-csrf-token', () => null)
  const backUrl = useRuntimeConfig().public.BACK_URL as string

  /** Ask the backend; null when nobody is signed in. Any other failure is left to the caller. */
  async function fetchMe(): Promise<AuthUser | null> {
    try {
      const me = await $fetch<Me>(`${backUrl}/auth/me`, { credentials: 'include' })
      user.value = me.user
      csrfToken.value = me.csrf_token
    }
    catch (error: any) {
      if (error?.response?.status !== 401)
        throw error
      forget()
    }
    return user.value
  }

  function forget() {
    user.value = null
    csrfToken.value = null
  }

  function loginUrl(provider: string, next = '/') {
    return `${backUrl}/auth/${provider}/login?next=${encodeURIComponent(next)}`
  }

  /** Close the session, then reload so nothing of the user stays in memory */
  async function logout() {
    try {
      await useNuxtApp().$api('/auth/logout', { method: 'POST' })
    }
    finally {
      forget()
      await navigateTo('/login', { external: true })
    }
  }

  return { user, csrfToken, fetchMe, forget, loginUrl, logout }
}
