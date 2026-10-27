<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Note } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// One entry of a journal: who wrote it and when, then the note itself. Its author edits it in place;
// the author or an owner deletes it. `item` names what it is about, when that isn't evident from the page.
const props = defineProps<{
  note: Note
  item?: { kind: Note['kind'], item_id: number, name: string } | null
  /** The thing it is about is read-only (an archived study): no editing, no deleting */
  readonly?: boolean
  /** Lighter and smaller, for a timeline where notes sit among shorter lines */
  compact?: boolean
}>()

const emit = defineEmits<{
  changed: []
}>()

const { updateNote, deleteNote } = useNoteActions()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { fail } = useStandardToast()

const edited = computed(() => props.note.updated_at !== props.note.created_at)

const editing = ref(false)
const draft = ref('')
const saving = ref(false)

function startEditing() {
  draft.value = props.note.body
  editing.value = true
}

async function save() {
  if (!draft.value.trim() || saving.value)
    return
  saving.value = true
  try {
    await updateNote(props.note.id, draft.value)
    editing.value = false
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t save the note', apiErrorMessage(error))
  }
  finally {
    saving.value = false
  }
}

const showDelete = ref(false)
const deleting = ref(false)

async function remove() {
  deleting.value = true
  try {
    await deleteNote(props.note.id)
    showDelete.value = false
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t delete the note', apiErrorMessage(error))
  }
  finally {
    deleting.value = false
  }
}

const menu = computed(() => [[
  ...(props.note.can_edit ? [{ label: 'Edit', icon: 'i-ph-pencil-simple-bold', onSelect: startEditing }] : []),
  ...(props.note.can_delete ? [{ label: 'Delete', icon: 'i-ph-trash-bold', color: 'error' as const, onSelect: () => { showDelete.value = true } }] : []),
]].filter(group => group.length))

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
    event.preventDefault()
    save()
  }
  else if (event.key === 'Escape') {
    editing.value = false
  }
}
</script>

<template>
  <article class="group/note rounded-lg border border-default bg-default" :class="compact ? 'px-3 py-2' : 'p-3'">
    <header class="flex items-center gap-2 text-xs text-muted">
      <UAvatar
        :src="note.author?.avatar_url ?? undefined"
        :alt="note.author?.display_name ?? 'Former member'"
        size="2xs"
      />
      <span class="truncate font-medium text-highlighted">{{ note.author?.display_name ?? 'Former member' }}</span>
      <span :title="formatDate(note.created_at)">{{ formatRelativeDate(note.created_at) }}</span>
      <span v-if="edited" class="text-muted" :title="`Edited ${formatDate(note.updated_at)}`">· edited</span>
      <template v-if="item">
        <span class="text-dimmed" aria-hidden="true">·</span>
        <NuxtLink
          :to="itemPath(item.kind, item.item_id)"
          class="inline-flex min-w-0 items-center gap-1 rounded text-toned outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
        >
          <UIcon :name="ITEM_KINDS[item.kind].icon" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
          <span class="truncate">{{ item.name }}</span>
        </NuxtLink>
      </template>

      <UDropdownMenu v-if="!readonly && menu.length && !editing" :items="menu" :content="{ align: 'end' }" class="ms-auto">
        <UButton
          icon="i-ph-dots-three-bold"
          color="neutral"
          variant="ghost"
          size="xs"
          aria-label="Note actions"
          class="ms-auto opacity-0 transition-opacity group-hover/note:opacity-100 pointer-coarse:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100"
        />
      </UDropdownMenu>
    </header>

    <div v-if="editing" class="mt-2" @keydown="onKeydown">
      <div class="rounded-md border border-default px-2 py-1 focus-within:ring-2 focus-within:ring-inverted">
        <NotesEditor v-model="draft" autofocus="end" placeholder="Write a note…" />
      </div>
      <div class="mt-2 flex items-center justify-end gap-2">
        <span class="me-auto text-xs text-muted">
          <BaseKbd value="meta" /> <BaseKbd value="enter" /> to save · <BaseKbd value="esc" /> to cancel
        </span>
        <UButton color="neutral" variant="ghost" size="sm" :disabled="saving" @click="() => { editing = false }">
          Cancel
        </UButton>
        <UButton color="neutral" size="sm" :loading="saving" :disabled="!draft.trim()" @click="save">
          Save
        </UButton>
      </div>
    </div>
    <NotesEditor v-else :class="compact ? 'mt-0.5' : 'mt-1'" :model-value="note.body" :editable="false" :compact="compact" />

    <BaseConfirmDialog
      v-model:open="showDelete"
      title="Delete note?"
      message="This can’t be undone."
      confirm-label="Delete"
      variant="error"
      :loading="deleting"
      @confirm="remove"
    />
  </article>
</template>
