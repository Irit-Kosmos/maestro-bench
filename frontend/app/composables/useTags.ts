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

import type { Tag, TagColor } from '~/types'

/**
 * Composable for tags, which prompts, analyses and agents share. The list is the same for
 * every component that asks for it, so a tag created in a picker shows up everywhere.
 */
export function useTags() {
  const { $api } = useNuxtApp()

  const { data, pending, refresh } = useMyLazyFetch<Tag[]>('/tags', {
    key: 'tags',
    default: () => [],
  })

  const tags = computed(() => data.value ?? [])

  async function createTag(name: string, color: TagColor) {
    const tag = await $api<Tag>('/tags', { method: 'POST', body: { name, color } })
    await refresh()
    return tag
  }

  async function updateTag(id: number, patch: { name?: string, color?: TagColor }) {
    const tag = await $api<Tag>(`/tags/${id}`, { method: 'PUT', body: patch })
    await refresh()
    return tag
  }

  async function deleteTag(id: number) {
    await $api(`/tags/${id}`, { method: 'DELETE' })
    await refresh()
  }

  /** Put tags on several items and take tags off them, leaving the rest of their tags be. */
  async function assignTags(kind: 'prompt' | 'analysis' | 'agent' | 'study', itemIds: number[], change: { add?: number[], remove?: number[] }) {
    await $api('/tags/assign', { method: 'POST', body: { kind, item_ids: itemIds, add: change.add ?? [], remove: change.remove ?? [] } })
    await refresh()
  }

  return { tags, pending, refreshTags: refresh, createTag, updateTag, deleteTag, assignTags }
}
