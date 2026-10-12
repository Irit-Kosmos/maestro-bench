<script setup lang="ts">
import type { NoteKind } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// The journal of an item or a study: a place to write a note, then the notes, newest first.
// What is written here is kept with the item and shows up in every study that holds it.
const props = defineProps<{
  kind: NoteKind
  itemId: number
  /** The thing is read-only (an archived study): the notes can be read, not written */
  readonly?: boolean
}>()

const emit = defineEmits<{
  /** A note was added, edited or deleted, which a study's timeline shows too */
  changed: []
}>()

const { notes, pending, error, refreshNotes, addNote } = useNotes(() => props.kind, () => props.itemId)
const { canEdit } = useCurrentWorkspace()
const { fail } = useStandardToast()

const writable = computed(() => canEdit.value && !props.readonly)

const draft = ref('')
const adding = ref(false)
const filled = computed(() => draft.value.trim().length > 0)

async function add() {
  if (!filled.value || adding.value)
    return
  adding.value = true
  try {
    await addNote(draft.value)
    draft.value = ''
    emit('changed')
  }
  catch (e) {
    fail('Couldn’t add the note', apiErrorMessage(e))
  }
  finally {
    adding.value = false
  }
}

function onEntryChanged() {
  refreshNotes()
  emit('changed')
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
    event.preventDefault()
    add()
  }
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div v-if="writable" class="rounded-lg border border-default bg-default focus-within:ring-2 focus-within:ring-inverted" @keydown="onKeydown">
      <div class="min-h-20 px-3 pt-2">
        <NotesEditor v-model="draft" placeholder="Write a note… type / for blocks" />
      </div>
      <div class="flex items-center justify-between gap-2 px-3 pb-2">
        <span class="text-xs text-muted">
          <BaseKbd value="meta" /> <BaseKbd value="enter" /> to add
        </span>
        <UButton color="neutral" size="sm" :loading="adding" :disabled="!filled" @click="add">
          Add note
        </UButton>
      </div>
    </div>

    <BaseLoadingState v-if="pending && !notes.length" />
    <BaseErrorState v-else-if="error && !notes.length" @retry="refreshNotes()" />
    <template v-else>
      <NotesEntry
        v-for="note in notes"
        :key="note.id"
        :note="note"
        :readonly="readonly"
        @changed="onEntryChanged"
      />
      <p v-if="!notes.length" class="text-sm text-muted">
        {{ writable ? 'No notes yet. Write down what you notice, what you decided and why.' : 'No notes yet.' }}
      </p>
    </template>
  </div>
</template>
