<script setup lang="ts">
import type { DatasetEditor, EditorRow } from '~/composables/useDatasetEditor'
import { useVirtualizer } from '@tanstack/vue-virtual'

// Virtualized spreadsheet-style view of a dataset: only the rows in view are in the DOM,
// so a 100k-row file scrolls as smoothly as a 100-row one. Rows have a fixed height for that;
// long text is read in the row panel or the cell editor.
const props = defineProps<{ editor: DatasetEditor }>()

const emit = defineEmits<{
  openRow: [index: number]
}>()

const ROW_HEIGHT = 36
const HEADER_HEIGHT = 32
const GUTTER_WIDTH = 72
const EDITOR_MIN_WIDTH = 360
const EDITOR_MAX_HEIGHT = 240

const { headers, columnWidths, displayedRows, selected, isReadOnly, version } = props.editor

const scrollEl = ref<HTMLElement | null>(null)

const active = ref({ row: 0, col: 0 })

interface CellEdit {
  key: number
  index: number
  col: number
  draft: string
}
const editing = ref<CellEdit | null>(null)
const editorEl = ref<HTMLTextAreaElement | null>(null)

const columnOffsets = computed(() => {
  let x = GUTTER_WIDTH
  return columnWidths.value.map((width) => {
    const left = x
    x += width
    return left
  })
})
const totalWidth = computed(() => columnWidths.value.reduce((sum, width) => sum + width, GUTTER_WIDTH))
const gridTemplate = computed(() => `${GUTTER_WIDTH}px ${columnWidths.value.map(width => `${width}px`).join(' ')}`)

const virtualizer = useVirtualizer(computed(() => ({
  count: displayedRows.value.length,
  getScrollElement: () => scrollEl.value,
  estimateSize: () => ROW_HEIGHT,
  getItemKey: (index: number) => displayedRows.value[index]?.key ?? index,
  scrollPaddingStart: HEADER_HEIGHT,
  overscan: 12,
})))
const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

const selectAllState = computed<boolean | 'indeterminate'>(() => {
  if (!selected.value.size)
    return false
  return displayedRows.value.every(row => selected.value.has(row.key)) ? true : 'indeterminate'
})

function toggleSelectAll() {
  if (selectAllState.value === true)
    props.editor.clearSelection()
  else
    props.editor.selectAllDisplayed()
}

// Cells are edited in place, so reading `version` makes the visible ones re-render
function valueAt(row: EditorRow, header: string): unknown {
  void version.value
  return row.values[header]
}

function textAt(row: EditorRow, header: string): string {
  return cellText(valueAt(row, header))
}

function cellClass(row: EditorRow, header: string, index: number, col: number) {
  return [
    active.value.row === index && active.value.col === col && 'ring-1 ring-inset ring-inverted',
    row.original === null || props.editor.isCellChanged(row, header) ? 'bg-warning/10' : '',
  ]
}

function focusGrid() {
  scrollEl.value?.focus({ preventScroll: true })
}

function scrollColumnIntoView(col: number) {
  const el = scrollEl.value
  const left = columnOffsets.value[col]
  const width = columnWidths.value[col]
  if (!el || left === undefined || width === undefined)
    return
  if (left < el.scrollLeft + GUTTER_WIDTH)
    el.scrollLeft = left - GUTTER_WIDTH
  else if (left + width > el.scrollLeft + el.clientWidth)
    el.scrollLeft = left + width - el.clientWidth
}

function setActive(row: number, col: number) {
  const lastRow = displayedRows.value.length - 1
  const lastCol = headers.value.length - 1
  if (lastRow < 0 || lastCol < 0)
    return
  active.value = {
    row: Math.min(Math.max(row, 0), lastRow),
    col: Math.min(Math.max(col, 0), lastCol),
  }
  virtualizer.value.scrollToIndex(active.value.row, { align: 'auto' })
  scrollColumnIntoView(active.value.col)
}

function activate(row: number, col: number) {
  active.value = { row, col }
  focusGrid()
}

function startEdit(index: number, col: number) {
  const row = displayedRows.value[index]
  const header = headers.value[col]
  if (!row || header === undefined || isReadOnly.value || !isEditableCell(row.values[header]))
    return

  setActive(index, col)
  editing.value = { key: row.key, index, col, draft: cellText(row.values[header]) }
}

watch(editing, async (edit) => {
  if (!edit)
    return
  await nextTick()
  const el = editorEl.value
  if (!el)
    return
  el.focus()
  el.setSelectionRange(el.value.length, el.value.length)
  autosizeEditor()
})

function autosizeEditor() {
  const el = editorEl.value
  if (!el)
    return
  el.style.height = 'auto'
  el.style.height = `${Math.min(Math.max(el.scrollHeight, ROW_HEIGHT), EDITOR_MAX_HEIGHT)}px`
}

function commitEdit(refocus = false) {
  const edit = editing.value
  if (!edit)
    return
  // Cleared first: removing the focused textarea fires blur, which lands back here
  editing.value = null

  const row = displayedRows.value[edit.index]
  const header = headers.value[edit.col]
  if (row && row.key === edit.key && header !== undefined)
    props.editor.setCell(row, header, edit.draft)
  if (refocus)
    nextTick(focusGrid)
}

function cancelEdit() {
  editing.value = null
  nextTick(focusGrid)
}

function commitAndMove(colDelta: number) {
  const edit = editing.value
  if (!edit)
    return
  commitEdit(true)
  nextTick(() => setActive(edit.index, edit.col + colDelta))
}

const pageSize = computed(() => {
  const height = scrollEl.value?.clientHeight ?? 0
  return Math.max(1, Math.floor((height - HEADER_HEIGHT) / ROW_HEIGHT) - 1)
})

function onKeydown(event: KeyboardEvent) {
  // Keys typed in the editor, checkboxes and buttons belong to them
  if (event.target !== scrollEl.value || event.metaKey || event.ctrlKey || event.altKey)
    return

  const { row, col } = active.value
  const current = displayedRows.value[row]

  switch (event.key) {
    case 'ArrowDown':
      setActive(row + 1, col)
      break
    case 'ArrowUp':
      setActive(row - 1, col)
      break
    case 'ArrowRight':
      setActive(row, col + 1)
      break
    case 'ArrowLeft':
      setActive(row, col - 1)
      break
    case 'PageDown':
      setActive(row + pageSize.value, col)
      break
    case 'PageUp':
      setActive(row - pageSize.value, col)
      break
    case 'Home':
      setActive(row, 0)
      break
    case 'End':
      setActive(row, headers.value.length - 1)
      break
    case 'Enter':
    case 'F2':
      startEdit(row, col)
      break
    case ' ':
      if (current)
        emit('openRow', row)
      break
    case 'x':
      if (current)
        props.editor.toggleSelected(current)
      break
    case 'Delete':
    case 'Backspace':
      if (isReadOnly.value || !selected.value.size)
        return
      props.editor.deleteSelected()
      break
    case 'Escape':
      if (!selected.value.size)
        return
      props.editor.clearSelection()
      break
    default:
      return
  }
  event.preventDefault()
}

// Searching or deleting can leave the active row past the end
watch(() => displayedRows.value.length, (length) => {
  if (active.value.row >= length)
    active.value = { row: Math.max(length - 1, 0), col: active.value.col }
})

const editorStyle = computed(() => {
  const edit = editing.value
  if (!edit)
    return undefined
  return {
    top: `${edit.index * ROW_HEIGHT}px`,
    left: `${columnOffsets.value[edit.col] ?? GUTTER_WIDTH}px`,
    width: `${Math.max(columnWidths.value[edit.col] ?? 0, EDITOR_MIN_WIDTH)}px`,
    minHeight: `${ROW_HEIGHT}px`,
  }
})

defineExpose({
  focus: focusGrid,
  reveal: (index: number) => setActive(index, active.value.col),
  startEdit: (index: number, col = 0) => nextTick(() => startEdit(index, col)),
})
</script>

<template>
  <div
    ref="scrollEl"
    role="grid"
    tabindex="0"
    aria-label="Dataset rows"
    :aria-rowcount="displayedRows.length"
    :aria-colcount="headers.length"
    class="h-full overflow-auto outline-none"
    @keydown="onKeydown"
  >
    <div :style="{ width: `${totalWidth}px`, minWidth: '100%' }">
      <!-- Header -->
      <div
        role="row"
        class="sticky top-0 z-20 grid border-b border-default bg-muted"
        :style="{ gridTemplateColumns: gridTemplate, height: `${HEADER_HEIGHT}px` }"
      >
        <div role="columnheader" class="sticky left-0 z-10 flex items-center pl-3 bg-inherit">
          <UCheckbox
            :model-value="selectAllState"
            size="sm"
            aria-label="Select all rows"
            :disabled="!displayedRows.length"
            @update:model-value="toggleSelectAll"
          />
        </div>
        <div
          v-for="header in headers"
          :key="header"
          role="columnheader"
          class="flex items-center px-3 text-xs font-medium font-mono text-muted truncate"
          :title="header"
        >
          <span class="truncate">{{ header }}</span>
        </div>
      </div>

      <!-- Rows: only those in view exist -->
      <div role="rowgroup" class="relative" :style="{ height: `${totalSize}px` }">
        <template v-for="item in virtualRows" :key="String(item.key)">
          <div
            v-if="displayedRows[item.index]"
            role="row"
            :aria-rowindex="item.index + 1"
            :aria-selected="selected.has(displayedRows[item.index]!.key)"
            class="group absolute top-0 left-0 grid w-full border-b border-default/60 hover:bg-elevated"
            :class="selected.has(displayedRows[item.index]!.key) ? 'bg-[color-mix(in_oklab,var(--ui-primary)_8%,var(--ui-bg))]' : 'bg-default'"
            :style="{ height: `${ROW_HEIGHT}px`, transform: `translateY(${item.start}px)`, gridTemplateColumns: gridTemplate }"
          >
            <div role="rowheader" class="sticky left-0 z-10 flex items-center gap-1 pl-3 pr-1 bg-inherit">
              <div class="flex items-center w-7 shrink-0">
                <span
                  class="text-xs text-dimmed tabular-nums group-hover:hidden"
                  :class="{ hidden: selected.has(displayedRows[item.index]!.key) }"
                >{{ item.index + 1 }}</span>
                <UCheckbox
                  :model-value="selected.has(displayedRows[item.index]!.key)"
                  size="sm"
                  :aria-label="`Select row ${item.index + 1}`"
                  class="group-hover:flex"
                  :class="selected.has(displayedRows[item.index]!.key) ? 'flex' : 'hidden'"
                  @update:model-value="editor.toggleSelected(displayedRows[item.index]!)"
                />
              </div>
              <UTooltip text="Open row" :kbds="['space']">
                <UButton
                  icon="i-ph-square-half-bold"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                  :aria-label="`Open row ${item.index + 1}`"
                  @click="emit('openRow', item.index)"
                />
              </UTooltip>
            </div>

            <div
              v-for="(header, col) in headers"
              :key="header"
              role="gridcell"
              class="flex items-center px-3 text-sm text-toned min-w-0"
              :class="cellClass(displayedRows[item.index]!, header, item.index, col)"
              @click="activate(item.index, col)"
              @dblclick="startEdit(item.index, col)"
            >
              <span
                v-if="valueAt(displayedRows[item.index]!, header) === null"
                class="text-dimmed"
              >null</span>
              <span
                v-else
                class="truncate"
                :title="textAt(displayedRows[item.index]!, header).length > 40 ? textAt(displayedRows[item.index]!, header) : undefined"
              >{{ textAt(displayedRows[item.index]!, header) }}</span>
            </div>
          </div>
        </template>

        <!-- Cell editor: one floating textarea in content coordinates, so it can grow past the row -->
        <textarea
          v-if="editing"
          ref="editorEl"
          v-model="editing.draft"
          rows="1"
          aria-label="Edit cell"
          class="absolute z-30 resize-none rounded-md border border-primary bg-default px-3 py-2 text-sm text-highlighted shadow-lg outline-none"
          :style="editorStyle"
          @input="autosizeEditor"
          @keydown.enter.exact.prevent="commitEdit(true)"
          @keydown.esc.prevent.stop="cancelEdit"
          @keydown.tab.exact.prevent="commitAndMove(1)"
          @keydown.tab.shift.prevent="commitAndMove(-1)"
          @blur="commitEdit()"
        />
      </div>
    </div>
  </div>
</template>
