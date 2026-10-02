<script setup lang="ts">
import type { DatasetEditor, EditorRow } from '~/composables/useDatasetEditor'

// One row with every field in full: the place to read and edit long text,
// which the grid's fixed-height cells truncate.
const props = defineProps<{
  editor: DatasetEditor
  row: EditorRow | null
  /** Position of the row among the rows currently shown */
  index: number
  total: number
}>()

const emit = defineEmits<{
  navigate: [delta: number]
  delete: []
}>()

const open = defineModel<boolean>('open', { default: false })

const { headers, isReadOnly, version } = props.editor

function textOf(header: string): string {
  void version.value
  return props.row ? cellText(props.row.values[header]) : ''
}

function canEdit(header: string): boolean {
  return !isReadOnly.value && !!props.row && isEditableCell(props.row.values[header])
}

function onInput(header: string, text: string) {
  if (props.row)
    props.editor.setCell(props.row, header, text)
}

// Typing in a field is left alone: these only fire outside inputs
defineShortcuts({
  j: () => open.value && emit('navigate', 1),
  k: () => open.value && emit('navigate', -1),
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="`Row ${index + 1}`"
    :description="`of ${total.toLocaleString('en-US')}${row?.original === null ? ' · new row' : ''}`"
    :ui="{ content: 'max-w-xl' }"
  >
    <template #body>
      <div v-if="row" class="flex flex-col gap-4">
        <div v-for="header in headers" :key="header">
          <label :for="`row-field-${header}`" class="flex items-center gap-2 mb-1 text-xs font-medium font-mono text-muted">
            {{ header }}
            <UBadge
              v-if="editor.isCellChanged(row, header)"
              label="edited"
              color="warning"
              variant="soft"
              size="sm"
              class="font-sans"
            />
          </label>
          <UTextarea
            :id="`row-field-${header}`"
            :model-value="textOf(header)"
            :readonly="!canEdit(header)"
            autoresize
            :rows="1"
            :maxrows="14"
            class="w-full"
            :ui="{ base: !canEdit(header) ? 'text-muted' : '' }"
            @update:model-value="onInput(header, $event as string)"
          />
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <div class="flex items-center gap-1">
          <UTooltip text="Previous row" :kbds="['k']">
            <UButton
              icon="i-lucide-chevron-up"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Previous row"
              :disabled="index <= 0"
              @click="emit('navigate', -1)"
            />
          </UTooltip>
          <UTooltip text="Next row" :kbds="['j']">
            <UButton
              icon="i-lucide-chevron-down"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Next row"
              :disabled="index >= total - 1"
              @click="emit('navigate', 1)"
            />
          </UTooltip>
        </div>
        <UButton
          v-if="!isReadOnly"
          icon="i-lucide-trash-2"
          label="Delete row"
          color="error"
          variant="ghost"
          size="sm"
          @click="emit('delete')"
        />
      </div>
    </template>
  </USlideover>
</template>
