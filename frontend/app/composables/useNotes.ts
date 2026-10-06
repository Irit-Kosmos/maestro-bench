import type { Note, NoteKind } from '~/types'

/** Composable for the journal of an item (or of a study): notes written in markdown, each with its author. */
export function useNotes(kind: MaybeRefOrGetter<NoteKind>, itemId: MaybeRefOrGetter<number>) {
  const { $api } = useNuxtApp()

  const { data, pending, error, refresh } = useMyLazyFetch<Note[]>('/notes', {
    key: () => `notes-${toValue(kind)}-${toValue(itemId)}`,
    query: computed(() => ({ kind: toValue(kind), item_id: toValue(itemId) })),
    default: () => [],
  })

  const notes = computed(() => data.value ?? [])

  async function addNote(body: string) {
    const note = await $api<Note>('/notes', { method: 'POST', body: { kind: toValue(kind), item_id: toValue(itemId), body } })
    await refresh()
    return note
  }

  return { notes, pending, error, refreshNotes: refresh, addNote }
}

/** Changes to a note that exist already, wherever it is shown (the journal, a study's timeline). */
export function useNoteActions() {
  const { $api } = useNuxtApp()

  const updateNote = (id: number, body: string) => $api<Note>(`/notes/${id}`, { method: 'PUT', body: { body } })
  const deleteNote = (id: number) => $api(`/notes/${id}`, { method: 'DELETE' })

  return { updateNote, deleteNote }
}
