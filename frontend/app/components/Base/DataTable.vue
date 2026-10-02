<script setup lang="ts">
import type { DropdownMenuItem, TableColumn } from '@nuxt/ui'
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
}

const props = withDefaults(defineProps<Props>(), {
  actions: () => [],
  loading: false,
  title: undefined,
  emptyMessage: 'No data available',
  searchable: false,
  rowTo: undefined,
  rowHint: undefined,
  itemName: undefined,
  itemNamePlural: undefined,
  totalCount: undefined,
  fill: false,
})

const emit = defineEmits<{
  refresh: []
}>()

const UButton = resolveComponent('UButton')
const UDropdownMenu = resolveComponent('UDropdownMenu')
const NuxtLink = resolveComponent('NuxtLink')

const slots = useSlots()
// Every slot but the toolbar goes to UTable (custom cells, headers)
const tableSlots = computed(() => Object.fromEntries(Object.entries(slots).filter(([name]) => name !== 'toolbar')))

// State
const searchQuery = ref('')
const searchInput = useTemplateRef<{ inputRef: HTMLInputElement | null }>('searchInput')

// Computed
const filteredData = computed(() => {
  if (!props.searchable || !searchQuery.value.trim()) {
    return props.data
  }

  const query = searchQuery.value.toLowerCase()
  return props.data.filter((item) => {
    return props.columns.some((column) => {
      const value = column.formatter ? column.formatter(item[column.key], item) : item[column.key]
      return String(value).toLowerCase().includes(query)
    })
  })
})

const countLabel = computed(() => {
  if (!props.itemName)
    return ''
  const total = props.totalCount ?? props.data.length
  const shown = filteredData.value.length
  const noun = total === 1 ? props.itemName : (props.itemNamePlural ?? `${props.itemName}s`)
  return shown === total ? `${total} ${noun}` : `${shown} of ${total} ${noun}`
})

const hasActions = computed(() => props.actions.length > 0)

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

if (props.searchable) {
  defineShortcuts({
    '/': () => searchInput.value?.inputRef?.focus(),
  })
}

// Methods
function handleRefresh() {
  emit('refresh')
}
</script>

<template>
  <div class="flex flex-col rounded-lg border border-default overflow-hidden" :class="fill && 'flex-1 min-h-0'">
    <!-- Toolbar -->
    <div class="flex shrink-0 items-center gap-2 px-2 h-11 border-b border-default">
      <UInput
        v-if="searchable"
        ref="searchInput"
        v-model="searchQuery"
        placeholder="Filter…"
        icon="i-lucide-search"
        size="sm"
        variant="none"
        aria-label="Filter rows"
        class="flex-1 max-w-sm"
        @keydown.esc="searchQuery = ''"
      >
        <template v-if="!searchQuery" #trailing>
          <UKbd value="/" size="sm" />
        </template>
      </UInput>
      <h3 v-else-if="title" class="px-2 text-sm font-medium text-highlighted">
        {{ title }}
      </h3>

      <!-- Page-specific filters -->
      <slot name="toolbar" />

      <span v-if="countLabel" class="ms-auto text-xs text-muted tabular-nums">
        {{ countLabel }}
      </span>
      <UTooltip text="Refresh">
        <UButton
          variant="ghost"
          color="neutral"
          icon="i-lucide-refresh-cw"
          size="sm"
          aria-label="Refresh"
          :loading="loading"
          :class="!countLabel && 'ms-auto'"
          @click="handleRefresh"
        />
      </UTooltip>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && filteredData.length === 0" class="p-6" :class="fill && 'flex-1 min-h-0 overflow-y-auto'">
      <BaseEmptyState
        :title="searchQuery ? 'No matching rows' : 'Nothing here yet'"
        :message="searchQuery ? `Nothing matches “${searchQuery}”. Try another term or clear the filter.` : emptyMessage"
        :icon="searchQuery ? 'i-lucide-search-x' : 'i-lucide-folder-open'"
        :action-label="searchQuery ? 'Clear filter' : undefined"
        action-icon="i-lucide-x"
        @action="searchQuery = ''"
      />
    </div>

    <!-- UTable -->
    <UTable
      v-else
      :data="filteredData"
      :columns="tableColumns"
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
