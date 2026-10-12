<script setup lang="ts">
import type { StudyDetail } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  study: StudyDetail
}>()

const emit = defineEmits<{
  changed: []
}>()

const { updateStudy } = useStudies()
const { canEdit } = useCurrentWorkspace()
const { fail } = useStandardToast()

const writable = computed(() => canEdit.value && props.study.status !== 'archived')

const editing = ref(false)
const draft = ref('')
const saving = ref(false)

function startEditing() {
  draft.value = props.study.description ?? ''
  editing.value = true
}

async function save() {
  saving.value = true
  try {
    await updateStudy(props.study.id, { description: draft.value.trim() || null })
    editing.value = false
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t save the description', apiErrorMessage(error))
  }
  finally {
    saving.value = false
  }
}

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
  <section>
    <div v-if="editing" @keydown="onKeydown">
      <div class="rounded-lg border border-default bg-default px-3 py-2 focus-within:ring-2 focus-within:ring-inverted">
        <NotesEditor v-model="draft" label="Study description" autofocus="end" placeholder="What is this study about? Type / for blocks" />
      </div>
      <div class="mt-2 flex items-center justify-end gap-2">
        <span class="me-auto text-xs text-muted">
          <BaseKbd value="meta" /> <BaseKbd value="enter" /> to save · <BaseKbd value="esc" /> to cancel
        </span>
        <UButton color="neutral" variant="ghost" size="sm" :disabled="saving" @click="() => { editing = false }">
          Cancel
        </UButton>
        <UButton size="sm" :loading="saving" @click="save">
          Save
        </UButton>
      </div>
    </div>

    <div v-else-if="study.description" class="group/description relative">
      <NotesEditor :model-value="study.description" :editable="false" />
      <UButton
        v-if="writable"
        icon="i-ph-pencil-simple-bold"
        color="neutral"
        variant="ghost"
        size="xs"
        aria-label="Edit the description"
        class="absolute -top-1 end-0 opacity-0 transition-opacity group-hover/description:opacity-100 pointer-coarse:opacity-100 focus-visible:opacity-100"
        @click="startEditing"
      />
    </div>

    <button
      v-else-if="writable"
      type="button"
      class="cursor-text rounded text-sm text-muted outline-none hover:text-toned focus-visible:ring-2 focus-visible:ring-inverted"
      @click="startEditing"
    >
      Add a description…
    </button>
  </section>
</template>
