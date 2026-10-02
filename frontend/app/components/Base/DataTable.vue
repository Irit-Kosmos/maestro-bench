<script setup lang="ts">
import type { DropdownMenuItem, TableColumn } from '@nuxt/ui'
import type { FilterSpec, FilterState } from '~/utils/filters'
import { h, resolveComponent } from 'vue'

interface Column {
  key: string
  label: string
  sortable?: boolean
  class?: string
  formatter?: (value: any, row: any) => string
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
}

const props = withDefaults(defineProps<Props>(), {
  actions: () => [],
  loading: false,
  title: undefined,
  emptyMessage: 'No data available',
  searchable: false,
  filters: () => [],
  rowTo: undefined,
  rowHint: undefined,
  itemName: undefined,
  itemNamePlural: undefined,
  totalCount: undefined,
  fill: false,
  selectable: false,
  rowKey: 'id',
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

// Convert our column format to UTable format
const tableColumns = computed<TableColumn<any>[]>(() => {
  const cols: TableColumn<any>[] = props.columns.map((col, index) => ({
    accessorKey: col.key,
    header: col.label,
    cell: ({ row }) => {
      const value = renderValue(col, row.getValue(col.key), row.original)
      if (index !== 0 || !props.rowTo)
        return value

      // Stretched link: the ::after covers the row, so the whole row is one target
      const hint = props.rowHint?.(row.original)
      return h(NuxtLink, {
        to: props.rowTo(row.original),
        class: 'flex items-baseline gap-2 min-w-0 font-medium text-highlighted outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-primary',
      }, () => [
        h('span', { class: 'truncate' }, value),
        hint ? h('span', { class: 'shrink-0 text-xs font-normal text-dimmed tabular-nums' }, hint) : null,
      ])
    },
    meta: {
      class: {
        td: col.class,
      },
    },
  }))

  if (props.selectable) {
    cols.unshift({
      id: 'select',
      header: ({ table }) => h(UCheckbox, {
        'modelValue': table.getIsSomePageRowsSelected() ? 'indeterminate' : table.getIsAllPageRowsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => table.toggleAllPageRowsSelected(!!value),
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
            'icon': 'i-lucide-ellipsis',
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
        icon="i-lucide-x"
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
        :icon="hasFilters ? 'i-lucide-search-x' : 'i-lucide-folder-open'"
        :action-label="hasFilters ? 'Clear filters' : undefined"
        action-icon="i-lucide-x"
        @action="clearFilters"
      />
    </div>

    <!-- UTable -->
    <UTable
      v-else
      v-model:row-selection="rowSelection"
      :data="filteredData"
      :columns="tableColumns"
      :get-row-id="(row: any) => String(row[rowKey])"
      :loading="loading"
      :empty="emptyMessage"
      class="min-w-full"
      :class="fill && 'flex-1 min-h-0'"
      :sticky="fill"
      :ui="{
        // Opaque when sticky, so rows don't show through while scrolling under it
        thead: fill ? 'bg-muted' : 'bg-muted/60',
        th: 'px-4 py-2 text-xs font-medium text-muted',
        tr: rowTo ? 'relative hover:bg-elevated/50' : '',
        td: 'px-4 py-2.5 text-sm text-toned',
      }"
    >
      <!-- Forward all dynamic slots to UTable -->
      <template v-for="(_, slotName) in tableSlots" :key="slotName" #[slotName]="slotProps">
        <slot :name="slotName" v-bind="slotProps" />
      </template>
    </UTable>
  </div>
</template>
