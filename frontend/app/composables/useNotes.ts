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
