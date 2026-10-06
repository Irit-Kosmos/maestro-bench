import type { Study, StudyDetail, StudyKind, StudyMembership, StudyStatus } from '~/types'

interface ItemRef {
  kind: StudyKind
  item_id: number
}

/**
 * Composable for studies: themes that gather experiments, batches and analyses. The list is the same
 * for every component that asks for it (sidebar, pickers, pages), so a study made in one shows up in all.
 *
 * Only the first component to ask reads the list. Every call to `useLazyFetch` with a key reads again when its
 * component mounts, and a component that mounts because the list stopped loading (or unmounts while it loads)
 * would then start the list loading again, over and over. The others share what the first one fetched, and
 * `refreshStudies` reads it again when a page wants it fresh.
 */
export function useStudies() {
  const { $api } = useNuxtApp()

  const requested = useState('studies-requested', () => false)
  const immediate = !requested.value
  requested.value = true

  const { data, pending, error, refresh } = useMyLazyFetch<Study[]>('/studies', {
    key: 'studies',
    default: () => [],
    immediate,
  })

  const studies = computed(() => data.value ?? [])

  async function createStudy(body: { name: string, description?: string | null, tag_ids?: number[], items?: ItemRef[] }) {
    const study = await $api<StudyDetail>('/studies', { method: 'POST', body })
    await refresh()
    return study
  }

  async function updateStudy(id: number, patch: { name?: string, description?: string | null, status?: StudyStatus, tag_ids?: number[] }) {
    const study = await $api<StudyDetail>(`/studies/${id}`, { method: 'PUT', body: patch })
    await refresh()
    return study
  }

  async function deleteStudy(id: number) {
    await $api(`/studies/${id}`, { method: 'DELETE' })
    await refresh()
  }

  async function addItems(id: number, items: ItemRef[]) {
    const study = await $api<StudyDetail>(`/studies/${id}/items`, { method: 'POST', body: { items } })
    await refresh()
    return study
  }

  async function removeItem(id: number, kind: StudyKind, itemId: number) {
    await $api(`/studies/${id}/items/${kind}/${itemId}`, { method: 'DELETE' })
    await refresh()
  }

  /** Put items in several studies and take them out of others, in one go. */
  async function assignStudies(kind: StudyKind, itemIds: number[], change: { add?: number[], remove?: number[] }) {
    await $api('/studies/assign', {
      method: 'POST',
      body: { kind, item_ids: itemIds, add: change.add ?? [], remove: change.remove ?? [] },
    })
    await refresh()
  }

  return { studies, pending, error, refreshStudies: refresh, createStudy, updateStudy, deleteStudy, addItems, removeItem, assignStudies }
}

/** Which study each item of a kind is in; shared by everything that shows or picks studies for that kind. */
export function useStudyMemberships(kind: MaybeRefOrGetter<StudyKind>) {
  const { data, refresh } = useMyLazyFetch<StudyMembership[]>('/studies/memberships', {
    key: () => `study-memberships-${toValue(kind)}`,
    query: computed(() => ({ kind: toValue(kind) })),
    default: () => [],
  })

  return { memberships: computed(() => data.value ?? []), refreshMemberships: refresh }
}
