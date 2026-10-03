<script setup lang="ts">
const props = defineProps<{
  datasetId: number
  /** Experiments that read this file; saving rewrites what they read */
  experimentCount: number | null
}>()

const toast = useToast()
const datasetId = toRef(props, 'datasetId')
const editor = useDatasetEditor(datasetId)
const {
  loading,
  saving,
  error,
  headers,
  rows,
  displayedRows,
  query,
  appliedQuery,
  selected,
  isDirty,
  isReadOnly,
  readOnlyReason,
  changeCount,
  editedCellCount,
  addedRowCount,
  deletedRowCount,
} = editor

const grid = useTemplateRef<{ focus: () => void, reveal: (index: number) => void, startEdit: (index: number, col?: number) => void }>('grid')
const searchInput = useTemplateRef<{ inputRef?: HTMLInputElement | null }>('searchInput')

const confirmOpen = ref(false)
const conflict = ref(false)

const panelOpen = ref(false)
const panelIndex = ref(0)
const panelRow = computed(() => displayedRows.value[panelIndex.value] ?? null)

const isFiltering = computed(() => appliedQuery.value.trim() !== '')

const countLabel = computed(() => {
  const total = rows.value.length.toLocaleString('en-US')
  return isFiltering.value ? `${displayedRows.value.length.toLocaleString('en-US')} of ${total}` : total
})

const changeSummary = computed(() => {
  const parts: string[] = []
  const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`
  if (editedCellCount.value)
    parts.push(`${plural(editedCellCount.value, 'cell')} edited`)
  if (addedRowCount.value)
    parts.push(`${plural(addedRowCount.value, 'row')} added`)
  if (deletedRowCount.value)
    parts.push(`${plural(deletedRowCount.value, 'row')} deleted`)
  return parts.join(' · ')
})

const confirmMessage = computed(() => {
  const n = props.experimentCount ?? 0
  return `This dataset is used in ${n} experiment${n === 1 ? '' : 's'}. Saving rewrites the file they read, so their results can no longer be reproduced from this data. Past results are kept.`
})

onMounted(() => {
  editor.load()
})

watch(datasetId, () => {
  conflict.value = false
  panelOpen.value = false
  editor.load()
})

// Saving
function requestSave() {
  if (!isDirty.value || isReadOnly.value || saving.value)
    return
  if (props.experimentCount)
    confirmOpen.value = true
  else
    doSave()
}

async function doSave() {
  const changes = changeCount.value
  const result = await editor.save()
  confirmOpen.value = false

  if (result.success) {
    conflict.value = false
    toast.add({
      title: 'Dataset saved',
      description: `${changes} change${changes === 1 ? '' : 's'} written to the file.`,
      color: 'success',
      icon: 'i-ph:check-circle-bold',
    })
    return
  }

  conflict.value = !!result.conflict
  toast.add({
    title: 'Couldn’t save the dataset',
    description: result.message,
    color: 'error',
    icon: 'i-ph:warning-circle-bold',
  })
}

function discardAll() {
  editor.discard()
  conflict.value = false
  panelOpen.value = false
}

async function reloadFromDisk() {
  conflict.value = false
  panelOpen.value = false
  await editor.load()
}

// Rows
async function addRow() {
  editor.addRow()
  await nextTick()
  grid.value?.startEdit(displayedRows.value.length - 1)
}

function openRow(index: number) {
  panelIndex.value = index
  panelOpen.value = true
}

function navigatePanel(delta: number) {
  const next = Math.min(Math.max(panelIndex.value + delta, 0), displayedRows.value.length - 1)
  panelIndex.value = next
  grid.value?.reveal(next)
}

function deletePanelRow() {
  const row = panelRow.value
  if (!row)
    return
  editor.deleteRows(new Set([row.key]))
  if (!displayedRows.value.length)
    panelOpen.value = false
  else
    panelIndex.value = Math.min(panelIndex.value, displayedRows.value.length - 1)
}

watch(panelOpen, (isOpen) => {
  if (!isOpen)
    nextTick(() => grid.value?.focus())
})

function onSearchEscape() {
  editor.clearSearch()
  searchInput.value?.inputRef?.blur()
  grid.value?.focus()
}

defineShortcuts({
  '/': () => searchInput.value?.inputRef?.focus(),
  'meta_s': {
    usingInput: true,
    handler: requestSave,
  },
})

// Unsaved edits live only in this tab
function warnBeforeUnload(event: BeforeUnloadEvent) {
  if (!isDirty.value)
    return
  event.preventDefault()
}

// Navigating away asks first; the answer comes from the dialog below
const leaveOpen = ref(false)
let resolveLeave: ((leave: boolean) => void) | null = null

function askLeave(): Promise<boolean> {
  if (!isDirty.value)
    return Promise.resolve(true)
  leaveOpen.value = true
  return new Promise((resolve) => {
    resolveLeave = resolve
  })
}

function settleLeave(leave: boolean) {
  resolveLeave?.(leave)
  resolveLeave = null
  leaveOpen.value = false
}

// Dismissing the dialog (Esc, backdrop) means staying
watch(leaveOpen, (isOpen) => {
  if (!isOpen)
    settleLeave(false)
})

onBeforeRouteLeave(askLeave)
onBeforeRouteUpdate(askLeave)

onMounted(() => window.addEventListener('beforeunload', warnBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', warnBeforeUnload))
</script>

<template>
  <div class="flex flex-col">
    <div v-if="loading" class="flex flex-col gap-3">
      <USkeleton class="h-11 w-full" />
      <USkeleton class="h-64 w-full" />
    </div>

    <UAlert
      v-else-if="error"
      color="error"
      variant="subtle"
      icon="i-ph-warning-circle-bold"
      title="Couldn’t open the dataset"
      :description="error"
      :actions="[{ label: 'Try again', color: 'error', variant: 'outline', onClick: () => { editor.load() } }]"
    />

    <div v-else class="flex flex-col flex-1 min-h-0 gap-3">
      <UAlert
        v-if="isReadOnly"
        color="neutral"
        variant="subtle"
        icon="i-ph-lock-bold"
        title="Read-only"
        :description="`${readOnlyReason}. You can search and read it, not edit it.`"
      />

      <UAlert
        v-if="conflict"
        color="warning"
        variant="subtle"
        icon="i-ph-warning-bold"
        title="The file changed on disk"
        description="It was modified after you opened it, so saving would overwrite that change. Reload to see it; your unsaved edits will be lost."
        :actions="[{ label: 'Reload and discard my edits', color: 'warning', variant: 'outline', onClick: reloadFromDisk }]"
      />

      <div class="flex flex-col flex-1 min-h-72 rounded-lg border border-default overflow-hidden">
        <!-- Toolbar -->
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1 px-2 min-h-11 border-b border-default">
          <UInput
            ref="searchInput"
            v-model="query"
            placeholder="Search all columns…"
            icon="i-ph-magnifying-glass-bold"
            size="sm"
            variant="none"
            aria-label="Search rows"
            class="flex-1 min-w-40 max-w-sm"
            @keydown.esc.prevent="onSearchEscape"
          >
            <template v-if="!query" #trailing>
              <UKbd value="/" size="sm" />
            </template>
          </UInput>

          <p class="text-xs text-muted tabular-nums whitespace-nowrap">
            <span class="font-medium text-highlighted">{{ countLabel }}</span>
            {{ rows.length === 1 ? 'row' : 'rows' }} · {{ headers.length }} columns
          </p>

          <div class="flex items-center gap-1.5 ml-auto">
            <template v-if="selected.size && !isReadOnly">
              <span class="text-xs text-muted tabular-nums">{{ selected.size.toLocaleString('en-US') }} selected</span>
              <UButton
                icon="i-ph-trash-bold"
                label="Delete"
                color="error"
                variant="ghost"
                size="sm"
                @click="editor.deleteSelected()"
              />
            </template>

            <template v-if="isDirty">
              <UTooltip :text="changeSummary">
                <span class="text-xs text-warning tabular-nums whitespace-nowrap">{{ changeCount.toLocaleString('en-US') }} unsaved</span>
              </UTooltip>
              <UButton
                label="Discard"
                color="neutral"
                variant="ghost"
                size="sm"
                :disabled="saving"
                @click="discardAll"
              />
              <UButton
                label="Save"
                color="primary"
                size="sm"
                :loading="saving"
                :kbds="['meta', 'S']"
                @click="requestSave"
              />
            </template>

            <UButton
              v-if="!isReadOnly"
              icon="i-ph-plus-bold"
              label="Add row"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="addRow"
            />
          </div>
        </div>

        <!-- Grid: takes the remaining height so rows scroll inside it and stay virtualized -->
        <div class="flex-1 min-h-0">
          <DatasetsGrid
            v-if="displayedRows.length"
            ref="grid"
            :editor="editor"
            @open-row="openRow"
          />

          <div v-else class="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
            <template v-if="isFiltering">
              <p class="text-sm text-muted text-pretty">
                No row matches “{{ appliedQuery }}”.
              </p>
              <UButton label="Clear search" color="neutral" variant="outline" size="sm" @click="editor.clearSearch()" />
            </template>
            <template v-else>
              <p class="text-sm text-muted">
                This file has no rows yet.
              </p>
              <UButton v-if="!isReadOnly" icon="i-ph-plus-bold" label="Add row" size="sm" @click="addRow" />
            </template>
          </div>
        </div>
      </div>

      <p class="hidden sm:block text-xs text-dimmed">
        <UKbd value="↑" size="sm" /> <UKbd value="↓" size="sm" /> move ·
        <UKbd value="enter" size="sm" /> edit ·
        <UKbd value="space" size="sm" /> open row ·
        <UKbd value="x" size="sm" /> select ·
        <UKbd value="⌘" size="sm" /> <UKbd value="S" size="sm" /> save
      </p>
    </div>

    <DatasetsRowPanel
      v-model:open="panelOpen"
      :editor="editor"
      :row="panelRow"
      :index="panelIndex"
      :total="displayedRows.length"
      @navigate="navigatePanel"
      @delete="deletePanelRow"
    />

    <BaseConfirmDialog
      v-model:open="leaveOpen"
      title="Leave without saving?"
      :message="`You have ${changeCount} unsaved change${changeCount === 1 ? '' : 's'} on this dataset. They’ll be lost.`"
      confirm-label="Leave"
      cancel-label="Stay"
      variant="warning"
      @confirm="settleLeave(true)"
    />

    <BaseConfirmDialog
      v-model:open="confirmOpen"
      title="Save changes to this dataset?"
      :message="confirmMessage"
      confirm-label="Save anyway"
      variant="warning"
      :loading="saving"
      @confirm="doSave"
    />
  </div>
</template>
