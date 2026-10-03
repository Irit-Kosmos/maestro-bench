import type { Tag, TagColor, TagWithCount } from '~/types'

/**
 * Composable for tags, which prompts, analyses and agents share. The list is the same for
 * every component that asks for it, so a tag created in a picker shows up everywhere.
 */
export function useTags() {
  const { $api } = useNuxtApp()

  const { data, pending, refresh } = useMyLazyFetch<TagWithCount[]>('/tags', {
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
  async function assignTags(kind: 'prompt' | 'analysis' | 'agent', itemIds: number[], change: { add?: number[], remove?: number[] }) {
    await $api('/tags/assign', { method: 'POST', body: { kind, item_ids: itemIds, add: change.add ?? [], remove: change.remove ?? [] } })
    await refresh()
  }

  return { tags, pending, refreshTags: refresh, createTag, updateTag, deleteTag, assignTags }
}
