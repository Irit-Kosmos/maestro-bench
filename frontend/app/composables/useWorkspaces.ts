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

import type { Workspace } from '~/types'

const LAST_WORKSPACE_KEY = 'maestro-workspace'

/**
 * The workspaces the signed-in user belongs to.
 *
 * Everything the app shows lives in one workspace at a time, named by the URL.
 * Changing workspace reloads the page, so nothing of the other one stays in memory.
 */
export function useWorkspaces() {
  const workspaces = useState<Workspace[] | null>('workspaces', () => null)
  const backUrl = useRuntimeConfig().public.BACK_URL as string

  async function load(): Promise<Workspace[]> {
    workspaces.value = await $fetch<Workspace[]>(`${backUrl}/workspaces`, { credentials: 'include' })
    return workspaces.value
  }

  /** The workspace to open when the URL names none: the one used last, else the first. */
  function defaultSlug(preferred?: string | null): string | null {
    const known = workspaces.value ?? []
    for (const candidate of [preferred, lastUsedSlug()]) {
      if (candidate && known.some(w => w.slug === candidate))
        return candidate
    }
    return known[0]?.slug ?? null
  }

  function lastUsedSlug(): string | null {
    try {
      return localStorage.getItem(LAST_WORKSPACE_KEY)
    }
    catch {
      return null
    }
  }

  function remember(slug: string) {
    try {
      localStorage.setItem(LAST_WORKSPACE_KEY, slug)
    }
    catch {
      // Private mode: the first workspace is the fallback
    }
  }

  /** Open a workspace (a full reload, on purpose) */
  function open(slug: string) {
    return navigateTo(inWorkspace(slug, '/'), { external: true })
  }

  async function create(name: string): Promise<Workspace> {
    const created = await useNuxtApp().$api<Workspace>('/workspaces', { method: 'POST', body: { name } })
    workspaces.value = [...(workspaces.value ?? []), created]
    return created
  }

  return { workspaces, load, defaultSlug, remember, open, create }
}
