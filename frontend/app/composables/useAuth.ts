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

import type { AuthUser } from '~/types'

interface Me {
  user: AuthUser
  csrf_token: string
  can_create_workspace: boolean
  public_sharing: boolean
}

/**
 * Who is signed in. The session lives in an HttpOnly cookie the page can't read:
 * `/auth/me` is how it learns who it is and which CSRF token to send with writes.
 */
export function useAuth() {
  const user = useState<AuthUser | null>('auth-user', () => null)
  const csrfToken = useState<string | null>('auth-csrf-token', () => null)
  const canCreateWorkspace = useState('auth-can-create-workspace', () => false)
  // Whether this instance lets items be shared through a public link
  const publicSharing = useState('auth-public-sharing', () => false)
  const backUrl = useRuntimeConfig().public.BACK_URL as string

  /** Ask the backend; null when nobody is signed in. Any other failure is left to the caller. */
  async function fetchMe(): Promise<AuthUser | null> {
    try {
      const me = await $fetch<Me>(`${backUrl}/auth/me`, { credentials: 'include' })
      user.value = me.user
      csrfToken.value = me.csrf_token
      canCreateWorkspace.value = me.can_create_workspace
      publicSharing.value = me.public_sharing
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

  return { user, csrfToken, canCreateWorkspace, publicSharing, fetchMe, forget, loginUrl, logout }
}
