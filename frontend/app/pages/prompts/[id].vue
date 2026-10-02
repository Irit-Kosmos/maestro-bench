<script setup lang="ts">
import type { PromptVersionFormValues } from '~/components/Prompt/PromptVersionForm.vue'
import type { Prompt, PromptVersion } from '~/types'

// Route params
const route = useRoute()
const router = useRouter()
const promptId = Number.parseInt(route.params.id as string)

// Composables
const { updatePrompt, getPromptVersions, createPromptVersion, updatePromptVersion, deletePromptVersion } = usePrompts()
const { showUpdateSuccess, showCreateSuccess, showDeleteSuccess, showUpdateError, showCreateError, showDeleteError } = useStandardToast()

// Fetch prompt details
const { data: prompt, refresh, pending, error } = await useMyLazyFetch<Prompt>(`/prompts/${promptId}`)

useBreadcrumbLabel(() => prompt.value?.name)

// Page meta
useSeoMeta({
  title: computed(() => prompt.value ? `${prompt.value.name} - Prompts` : 'Prompt Details'),
  description: computed(() => prompt.value?.description || 'View and manage prompt versions'),
})

// Versions: newest first. Which one is the default is shown on its row, not by its position.
const versions = ref<PromptVersion[]>([])
const versionsLoading = ref(true)

const sortedVersions = computed(() =>
  [...versions.value].sort((a, b) => parseApiDate(b.created_at).getTime() - parseApiDate(a.created_at).getTime()),
)

async function loadVersions() {
  versionsLoading.value = true
  try {
    const result = await getPromptVersions(promptId)
    if (result.success)
      versions.value = (result.data as PromptVersion[]) || []
  }
  catch {
    console.error('Error loading versions')
  }
  finally {
    versionsLoading.value = false
  }
}

// The selected version lives in the URL (?v=), so a refresh or a shared link lands on the same one
const selectedId = computed<number | null>({
  get() {
    const fromQuery = Number.parseInt(String(route.query.v))
    if (versions.value.some(version => version.id === fromQuery))
      return fromQuery
    return (versions.value.find(version => version.is_default) ?? sortedVersions.value[0])?.id ?? null
  },
  set(id) {
    router.replace({ query: { ...route.query, v: id ?? undefined } })
  },
})

const selected = computed(() => versions.value.find(version => version.id === selectedId.value) ?? null)

// On desktop the block fills the page (top bar and body padding taken off), so only the panes inside scroll
const frame = 'min-h-[26rem] overflow-hidden rounded-lg border border-default lg:h-[calc(100dvh-var(--ui-header-height)-3rem-1px)]'

// What the right-hand pane is doing
const mode = ref<'view' | 'edit' | 'create'>('view')
const saving = ref(false)

function emptyForm(): PromptVersionFormValues {
  return { version: '', system_prompt: '', user_prompt: '', variables: [], notes: '', is_active: true, is_default: false }
}

function formFrom(version: PromptVersion): PromptVersionFormValues {
  return {
    version: version.version,
    system_prompt: version.system_prompt || '',
    user_prompt: version.user_prompt || '',
    variables: parseVariables(version.variables || ''),
    notes: version.notes || '',
    is_active: version.is_active,
    is_default: version.is_default,
  }
}

const form = ref<PromptVersionFormValues>(emptyForm())
// Compared against to know whether leaving would lose work
const initialForm = ref(JSON.stringify(form.value))
const dirty = computed(() => mode.value !== 'view' && JSON.stringify(form.value) !== initialForm.value)

function openForm(next: 'edit' | 'create', values: PromptVersionFormValues) {
  form.value = values
  initialForm.value = JSON.stringify(values)
  mode.value = next
}

function startEdit() {
  if (selected.value)
    openForm('edit', formFrom(selected.value))
}

// A new version starts as a copy of the one on screen: prompts are iterated, not rewritten
function startCreate() {
  const base = selected.value ? formFrom(selected.value) : emptyForm()
  openForm('create', { ...base, version: '', notes: '', is_default: false })
}

// Leaving the form with unsaved changes asks first; everything else goes straight through
const showDiscardDialog = ref(false)
let afterDiscard: (() => void) | null = null

function guard(action: () => void) {
  if (!dirty.value) {
    action()
    return
  }
  afterDiscard = action
  showDiscardDialog.value = true
}

function confirmDiscard() {
  showDiscardDialog.value = false
  mode.value = 'view'
  afterDiscard?.()
  afterDiscard = null
}

function cancelForm() {
  guard(() => {
    mode.value = 'view'
  })
}

function select(id: number) {
  if (id === selectedId.value && mode.value !== 'create')
    return
  guard(() => {
    mode.value = 'view'
    selectedId.value = id
  })
}

function payloadFrom(values: PromptVersionFormValues) {
  return {
    version: values.version.trim(),
    system_prompt: values.system_prompt.trim() || null,
    user_prompt: values.user_prompt.trim() || null,
    variables: stringifyVariables(values.variables) || null,
    notes: values.notes.trim() || null,
    is_active: values.is_active,
    is_default: values.is_default,
  }
}

async function save() {
  saving.value = true
  try {
    if (mode.value === 'create') {
      const result = await createPromptVersion(promptId, payloadFrom(form.value))
      if (!result.success)
        return showCreateError('Version', typeof result.error === 'string' ? result.error : undefined)
      showCreateSuccess('Version')
      await loadVersions()
      mode.value = 'view'
      selectedId.value = (result.data as PromptVersion).id
    }
    else if (selected.value) {
      const result = await updatePromptVersion(selected.value.id, payloadFrom(form.value))
      if (!result.success)
        return showUpdateError('Version', typeof result.error === 'string' ? result.error : undefined)
      showUpdateSuccess('Version')
      await loadVersions()
      mode.value = 'view'
    }
  }
  catch (err) {
    const message = err instanceof Error ? err.message : undefined
    if (mode.value === 'create')
      showCreateError('Version', message)
    else
      showUpdateError('Version', message)
  }
  finally {
    saving.value = false
  }
}

// One-click changes from the actions menu
async function patchSelected(patch: { is_default?: boolean, is_active?: boolean }) {
  if (!selected.value)
    return
  const result = await updatePromptVersion(selected.value.id, patch)
  if (result.success)
    await loadVersions()
  else
    showUpdateError('Version', typeof result.error === 'string' ? result.error : undefined)
}

// Delete
const showDeleteDialog = ref(false)
const deleting = ref(false)

async function confirmDelete() {
  if (!selected.value)
    return
  deleting.value = true
  try {
    const result = await deletePromptVersion(selected.value.id)
    if (!result.success)
      return showDeleteError('Version', typeof result.error === 'string' ? result.error : undefined)
    showDeleteSuccess('Version')
    showDeleteDialog.value = false
    selectedId.value = null
    await loadVersions()
  }
  catch (err) {
    showDeleteError('Version', err instanceof Error ? err.message : undefined)
  }
  finally {
    deleting.value = false
  }
}

// Prompt details (name, description, category): rare, so a small modal is enough
const showEditPromptModal = ref(false)
const updatingPrompt = ref(false)
const editPromptData = ref({ name: '', description: '', category: '' })

watch(prompt, (value) => {
  if (value) {
    editPromptData.value = {
      name: value.name,
      description: value.description || '',
      category: value.category || '',
    }
  }
}, { immediate: true })

onMounted(loadVersions)

async function handleEditPrompt() {
  if (!editPromptData.value.name.trim())
    return
  updatingPrompt.value = true
  try {
    const result = await updatePrompt(promptId, editPromptData.value)
    if (!result.success)
      return showUpdateError('Prompt', typeof result.error === 'string' ? result.error : undefined)
    showUpdateSuccess('Prompt')
    showEditPromptModal.value = false
    await refresh()
  }
  catch (err) {
    showUpdateError('Prompt', err instanceof Error ? err.message : undefined)
  }
  finally {
    updatingPrompt.value = false
  }
}

// Keyboard: arrows or j/k to move through versions, e to edit, n for a new one.
// Typing in a field never triggers them, and the form has its own ⌘↵ / Esc.
// Esc is also caught here, for when focus is nowhere in the form (right after clicking Edit).
const anyDialogOpen = computed(() => showEditPromptModal.value || showDeleteDialog.value || showDiscardDialog.value)

function step(direction: 1 | -1) {
  if (mode.value !== 'view' || anyDialogOpen.value)
    return
  const list = sortedVersions.value
  const index = list.findIndex(version => version.id === selectedId.value)
  const next = list[Math.min(list.length - 1, Math.max(0, index + direction))]
  if (next)
    selectedId.value = next.id
}

defineShortcuts({
  arrowdown: () => step(1),
  j: () => step(1),
  arrowup: () => step(-1),
  k: () => step(-1),
  e: () => {
    if (mode.value === 'view' && !anyDialogOpen.value)
      startEdit()
  },
  n: () => {
    if (mode.value === 'view' && !anyDialogOpen.value)
      startCreate()
  },
  escape: () => {
    if (mode.value !== 'view' && !anyDialogOpen.value)
      cancelForm()
  },
})

// Leaving the page with unsaved edits
onBeforeRouteLeave((to) => {
  if (!dirty.value)
    return
  guard(() => router.push(to.fullPath))
  return false
})
</script>

<template>
  <BasePageContent
    :loading="pending && !prompt"
    :error="error ? 'Unable to load prompt details. Please try again.' : null"
  >
    <template #before-content>
      <UButton
        variant="outline"
        color="neutral"
        icon="i-lucide-pencil"
        size="sm"
        @click="() => { showEditPromptModal = true }"
      >
        Edit
      </UButton>
      <UButton
        color="primary"
        icon="i-lucide-plus"
        size="sm"
        :disabled="mode === 'create'"
        @click="guard(startCreate)"
      >
        New version
      </UButton>
    </template>

    <template v-if="prompt">
      <div v-if="versionsLoading && versions.length === 0" :class="frame" class="animate-pulse bg-muted/40" />

      <BaseEmptyState
        v-else-if="versions.length === 0 && mode !== 'create'"
        title="No versions yet"
        message="Create the first version of this prompt to get started."
        icon="i-lucide-file-text"
        action-label="New version"
        @action="startCreate"
      />

      <div v-else :class="frame" class="grid lg:grid-cols-[15rem_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)]">
        <PromptVersionList
          :versions="sortedVersions"
          :selected-id="selectedId"
          :drafting="mode === 'create'"
          class="max-h-56 border-b border-default bg-muted/30 lg:max-h-none lg:border-e lg:border-b-0"
          @select="select"
          @create="guard(startCreate)"
        />

        <PromptVersionForm
          v-if="mode !== 'view'"
          v-model="form"
          :mode="mode"
          :saving="saving"
          @save="save"
          @cancel="cancelForm"
        />
        <PromptVersionView
          v-else-if="selected"
          :key="selected.id"
          :version="selected"
          @edit="startEdit"
          @set-default="patchSelected({ is_default: true })"
          @toggle-active="patchSelected({ is_active: !selected.is_active })"
          @delete="() => { showDeleteDialog = true }"
        />
      </div>
    </template>

    <!-- Prompt details -->
    <BaseCrudModal
      v-model:open="showEditPromptModal"
      title="Prompt"
      mode="edit"
      :loading="updatingPrompt"
      @submit="handleEditPrompt"
    >
      <UFormField label="Name" required>
        <UInput v-model="editPromptData.name" placeholder="Enter prompt name" autocomplete="off" class="w-full" />
      </UFormField>
      <UFormField label="Description">
        <UTextarea v-model="editPromptData.description" placeholder="What this prompt is for" :rows="3" class="w-full" />
      </UFormField>
      <UFormField label="Category">
        <UInput v-model="editPromptData.category" placeholder="e.g. evaluation, instruction" autocomplete="off" class="w-full" />
      </UFormField>
    </BaseCrudModal>

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete version"
      :message="`Are you sure you want to delete version &quot;${selected?.version}&quot;? This action cannot be undone.`"
      confirm-label="Delete version"
      variant="error"
      :loading="deleting"
      @confirm="confirmDelete"
    />

    <BaseConfirmDialog
      v-model:open="showDiscardDialog"
      title="Discard changes?"
      message="This version has unsaved changes that will be lost."
      confirm-label="Discard"
      variant="warning"
      @confirm="confirmDiscard"
    />
  </BasePageContent>
</template>
