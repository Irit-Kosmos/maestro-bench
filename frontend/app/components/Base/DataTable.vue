<script setup lang="ts">
import type { DropdownMenuItem, TableColumn } from '@nuxt/ui'
import type { VNodeChild } from 'vue'
import type { FilterSpec, FilterState } from '~/utils/filters'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { h, resolveComponent } from 'vue'

interface Column {
  key: string
  label: string
  sortable?: boolean
  class?: string
  /** Width in px. Once a column has one, the table stops sizing columns by their content (see `fixedLayout`) and
   * the columns without one share what is left; their content is truncated to fit */
  width?: number
  formatter?: (value: any, row: any) => string
  /** Rich content for the first column of a linked row (see `rowTo`); it places the row hint itself. `formatter` still feeds the search */
  render?: (row: any, hint?: string) => VNodeChild
}

interface Action {
  label: string | ((item: any) => string)
  icon?: string
  variant?: 'solid' | 'outline' | 'ghost'
  color?: 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'
  size?: 'xs' | 'sm' | 'md'
  handler: (item: any) => void
  show?: (item: any) => boolean
}

interface Props {
  data: any[]
  columns: Column[]
  actions?: Action[]
  loading?: boolean
  title?: string
  emptyMessage?: string
  searchable?: boolean
  /** Filters offered next to the search; their options are found in `data` (see `FilterSpec`) */
  filters?: FilterSpec<any>[]
  actionTo?: string
  /** Makes every row a link: the first column becomes the row's link, the whole row is clickable */
  rowTo?: (item: any) => string
  /** Like `rowTo`, for a row that opens something on the page (a panel) instead of going elsewhere: the first column
   * becomes a button. `rowTo` wins when both are given */
  rowOpen?: (item: any) => void
  /** Key of the row whose panel is open, to mark it in the list */
  activeKey?: string | number | null
  /** Muted text next to the first column, e.g. an id */
  rowHint?: (item: any) => string | undefined
  /** Noun used in the count, e.g. "experiment" → "12 experiments" */
  itemName?: string
  itemNamePlural?: string
  /** Total before page-level filters, so the count reads "4 of 41" */
  totalCount?: number
  /** Fills the height of its parent: toolbar and column headers stay put, only the rows scroll */
  fill?: boolean
  /** Adds a checkbox column; the toolbar turns into a selection bar (see the `selection-actions` slot) */
  selectable?: boolean
  /** Property that identifies a row in `v-model:selected` */
  rowKey?: string
  /** Virtualizes the rows so a long list stays light: only those in view are in the DOM. Needs `fill` (the rows scroll
   * inside the table) and a fixed row height in px, which every row must fit in, so no wrapping content */
  rowHeight?: number
}

const props = withDefaults(defineProps<Props>(), {
  actions: () => [],
  loading: false,
  title: undefined,
  emptyMessage: 'No data available',
  searchable: false,
  filters: () => [],
  rowTo: undefined,
  rowOpen: undefined,
  activeKey: null,
  rowHint: undefined,
  itemName: undefined,
  itemNamePlural: undefined,
  totalCount: undefined,
  fill: false,
  selectable: false,
  rowKey: 'id',
  rowHeight: undefined,
})

const emit = defineEmits<{
  refresh: []
}>()

const UButton = resolveComponent('UButton')
const UDropdownMenu = resolveComponent('UDropdownMenu')
const NuxtLink = resolveComponent('NuxtLink')

const UCheckbox = resolveComponent('UCheckbox')

const slots = useSlots()
// Every slot but the toolbar ones goes to UTable (custom cells, headers)
const tableSlots = computed(() => Object.fromEntries(Object.entries(slots).filter(([name]) => name !== 'toolbar' && name !== 'selection-actions')))

// Keys of the selected rows
const selected = defineModel<(string | number)[]>('selected', { default: () => [] })

// What is picked in the filters; bind it to seed or persist it, otherwise the table keeps it to itself
const filterState = defineModel<FilterState>('filterState', { default: () => ({}) })

// Search matches what the columns display
const { search, definitions, filtered: filteredData, hasFilters, clear: clearFilters } = useListFilters(
  () => props.data,
  () => props.filters,
  row => props.columns.map(column => renderValue(column, row[column.key], row) ?? '').join(' '),
  filterState,
)

const total = computed(() => props.totalCount ?? props.data.length)

const hasActions = computed(() => props.actions.length > 0)

// Columns sized by their content shift as rows come and go (filtering, scrolling a virtualized list), so widths are
// declared instead. Opt-in: a table that never sets a `width` keeps sizing itself
const SELECT_WIDTH = 40
const ACTIONS_WIDTH = 48
const FLEX_MIN_WIDTH = 200
const fixedLayout = computed(() => props.columns.some(column => column.width))
// Below this the table scrolls sideways instead of squeezing the flexible columns to nothing
const tableMinWidth = computed(() => props.columns.reduce((sum, column) => sum + (column.width ?? FLEX_MIN_WIDTH), 0)
  + (props.selectable ? SELECT_WIDTH : 0) + (hasActions.value ? ACTIONS_WIDTH : 0))

// Virtualized rows: UTable is given only the rows in view, and two spacer rows stand in for the others. That keeps the
// table as tall as the whole list, which is what lets the header stay stuck to the top all the way down
const virtualized = computed(() => props.fill && !!props.rowHeight)
const tableEl = ref<{ $el: HTMLElement } | null>(null)
const virtualizer = useVirtualizer(computed(() => ({
  count: filteredData.value.length,
  getScrollElement: () => tableEl.value?.$el ?? null,
  estimateSize: () => props.rowHeight ?? 0,
  getItemKey: (index: number) => filteredData.value[index]?.[props.rowKey] ?? index,
  overscan: 12,
  enabled: virtualized.value,
  // Something to render before the scroll area is measured, server side included
  initialRect: { width: 0, height: 800 },
})))
const virtualItems = computed(() => virtualizer.value.getVirtualItems())
const tableRows = computed(() => virtualized.value
  ? virtualItems.value.flatMap(item => filteredData.value[item.index] ?? [])
  : filteredData.value)
const spaceBefore = computed(() => virtualItems.value[0]?.start ?? 0)
const spaceAfter = computed(() => {
  const last = virtualItems.value.at(-1)
  return last ? virtualizer.value.getTotalSize() - last.end : 0
})

// The header checkbox covers every row of the list, not only those in the DOM
const allSelectedState = computed<boolean | 'indeterminate'>(() => {
  if (!selected.value.length)
    return false
  const keys = new Set(selected.value)
  return filteredData.value.every(row => keys.has(row[props.rowKey])) ? true : 'indeterminate'
})

function toggleSelectAll(value: boolean | 'indeterminate') {
  selected.value = value ? filteredData.value.map(row => row[props.rowKey]) : []
}

// UTable tracks selection as { [rowId]: true }
const rowSelection = computed({
  get: () => Object.fromEntries(selected.value.map(key => [key, true])),
  set: (state: Record<string, boolean>) => {
    selected.value = filteredData.value
      .map(row => row[props.rowKey])
      .filter(key => state[String(key)])
  },
})

// Rows that were filtered out or deleted can't stay selected, or a bulk action would hit rows nobody sees
watch(filteredData, (rows) => {
  if (!selected.value.length)
    return
  const visible = new Set(rows.map(row => row[props.rowKey]))
  const kept = selected.value.filter(key => visible.has(key))
  if (kept.length !== selected.value.length)
    selected.value = kept
})

// What the table shows, once searched and filtered, for pages that move through it
defineExpose({ rows: filteredData })

const selectedRows = computed(() => filteredData.value.filter(row => selected.value.includes(row[props.rowKey])))

function renderValue(col: Column, value: any, row: any) {
  return col.formatter ? col.formatter(value, row) : value
}

function menuItems(row: any): DropdownMenuItem[] {
  return props.actions
    .filter(action => action.show ? action.show(row) : true)
    .map(action => ({
      label: typeof action.label === 'function' ? action.label(row) : action.label,
      icon: action.icon,
      color: action.color === 'error' ? 'error' : undefined,
      onSelect: () => action.handler(row),
    }))
}

// A row is exactly this tall, which is what the spacers rely on
const rowStyle = computed(() => virtualized.value ? { height: `${props.rowHeight}px` } : undefined)

// The row whose panel is open stays marked
const tableMeta = computed(() => ({
  class: {
    tr: (row: { original: any }) => props.activeKey != null && row.original[props.rowKey] === props.activeKey ? 'bg-elevated/70' : '',
  },
}))

// Convert our column format to UTable format
const tableColumns = computed<TableColumn<any>[]>(() => {
  const cols: TableColumn<any>[] = props.columns.map((col, index) => ({
    accessorKey: col.key,
    header: col.label,
    cell: ({ row }) => {
      const value = renderValue(col, row.getValue(col.key), row.original)
      if (index !== 0 || !(props.rowTo || props.rowOpen))
        return value

      // Stretched link: the ::after covers the row, so the whole row is one target
      const hint = props.rowHint?.(row.original)
      const linkClass = 'flex items-baseline gap-2 min-w-0 font-medium text-highlighted outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-inverted'
      const content = () => col.render
        ? col.render(row.original, hint)
        : [
            h('span', { class: 'truncate' }, value),
            hint ? h('span', { class: 'shrink-0 text-xs font-normal text-dimmed tabular-nums' }, hint) : null,
          ]
      if (props.rowTo)
        return h(NuxtLink, { to: props.rowTo(row.original), class: linkClass }, content)
      // Native button, which the table's own row click leaves alone
      return h('button', { type: 'button', class: `${linkClass} w-full text-left`, onClick: () => props.rowOpen?.(row.original) }, [content()])
    },
    meta: {
      class: {
        td: col.class,
      },
      style: {
        th: col.width ? { width: `${col.width}px` } : undefined,
        td: rowStyle.value,
      },
    },
  }))

  if (props.selectable) {
    cols.unshift({
      id: 'select',
      header: () => h(UCheckbox, {
        'modelValue': allSelectedState.value,
        'onUpdate:modelValue': toggleSelectAll,
        'aria-label': 'Select all rows',
      }),
      cell: ({ row }) => h(UCheckbox, {
        'modelValue': row.getIsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
        'aria-label': 'Select row',
        // Above the row's stretched link, so ticking doesn't open the row
        'class': 'relative z-1',
      }),
      meta: {
        class: {
          th: 'w-10 pe-0',
          td: 'w-10 pe-0',
        },
        style: { td: rowStyle.value },
      },
    })
  }

  if (hasActions.value) {
    cols.push({
      id: 'actions',
      header: () => h('span', { class: 'sr-only' }, 'Actions'),
      cell: ({ row }) => {
        const items = menuItems(row.original)
        if (!items.length)
          return null
        return h(UDropdownMenu, { items, content: { align: 'end' } }, () =>
          h(UButton, {
            'icon': 'i-ph-dots-three-bold',
            'color': 'neutral',
            'variant': 'ghost',
            'size': 'sm',
            'class': 'relative z-1',
            'aria-label': 'Row actions',
          }))
      },
      meta: {
        class: {
          th: 'w-12',
          td: 'w-12 text-right',
        },
        style: { td: rowStyle.value },
      },
    })
  }

  return cols
})
</script>

<template>
  <div class="flex flex-col rounded-lg border border-default overflow-hidden" :class="fill && 'flex-1 min-h-0'">
    <!-- Selection bar -->
    <div v-if="selectable && selected.length" class="flex shrink-0 items-center gap-2 px-2 h-11 border-b border-default bg-elevated/50">
      <span class="px-2 text-sm font-medium text-highlighted tabular-nums">
        {{ selected.length }} selected
      </span>
      <slot name="selection-actions" :rows="selectedRows" />
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-x-bold"
        size="sm"
        class="ms-auto"
        @click="selected = []"
      >
        Clear
      </UButton>
    </div>

    <!-- Toolbar -->
    <BaseListToolbar
      v-else
      v-model:search="search"
      v-model:filters="filterState"
      :definitions="definitions"
      :total="total"
      :shown="filteredData.length"
      :item-name="itemName"
      :item-name-plural="itemNamePlural"
      :title="title"
      :searchable="searchable"
      :loading="loading"
      @refresh="emit('refresh')"
    >
      <!-- Page-specific filters -->
      <slot name="toolbar" />
    </BaseListToolbar>

    <!-- Empty State -->
    <div v-if="!loading && filteredData.length === 0" class="p-6" :class="fill && 'flex-1 min-h-0 overflow-y-auto'">
      <BaseEmptyState
        :title="hasFilters ? 'No matching rows' : 'Nothing here yet'"
        :message="hasFilters ? 'Try another search, or clear the filters.' : emptyMessage"
        :icon="hasFilters ? 'i-ph-magnifying-glass-bold' : 'i-ph-folder-open-bold'"
        :action-label="hasFilters ? 'Clear filters' : undefined"
        action-icon="i-ph-x-bold"
        @action="clearFilters"
      />
    </div>

    <!-- UTable -->
    <UTable
      v-else
      ref="tableEl"
      v-model:row-selection="rowSelection"
      :data="tableRows"
      :columns="tableColumns"
      :get-row-id="(row: any) => String(row[rowKey])"
      :loading="loading"
      :empty="emptyMessage"
      class="min-w-full"
      :class="fill && 'flex-1 min-h-0'"
      :sticky="fill"
      :meta="tableMeta"
      :style="fixedLayout ? { '--table-min-width': `${tableMinWidth}px` } : undefined"
      :ui="{
        base: fixedLayout ? 'w-full min-w-(--table-min-width) table-fixed' : '',
        // Opaque when sticky, so rows don't show through while scrolling under it
        thead: fill ? 'bg-muted' : 'bg-muted/60',
        // Virtualized, the separators are drawn inside the cells: a border would add to the fixed row height
        tbody: virtualized ? 'divide-y-0' : '',
        th: 'px-4 py-2 text-xs font-medium text-muted',
        tr: rowTo || rowOpen ? 'relative hover:bg-elevated/50' : '',
        td: ['px-4 py-2.5 text-sm text-toned', fixedLayout && 'overflow-hidden text-ellipsis', virtualized && 'shadow-[inset_0_-1px_0_var(--ui-border)]'],
      }"
    >
      <!-- Stand-ins for the rows above and below the ones in the DOM -->
      <template v-if="virtualized" #body-top>
        <tr v-if="spaceBefore > 0" aria-hidden="true">
          <td :colspan="tableColumns.length" class="p-0" :style="{ height: `${spaceBefore}px` }" />
        </tr>
      </template>
      <template v-if="virtualized" #body-bottom>
        <tr v-if="spaceAfter > 0" aria-hidden="true">
          <td :colspan="tableColumns.length" class="p-0" :style="{ height: `${spaceAfter}px` }" />
        </tr>
      </template>

      <!-- Forward all dynamic slots to UTable -->
      <template v-for="(_, slotName) in tableSlots" :key="slotName" #[slotName]="slotProps">
        <slot :name="slotName" v-bind="slotProps" />
      </template>
    </UTable>
  </div>
</template>
