<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { h, resolveComponent } from 'vue'

interface Column {
  key: string
  label: string
  sortable?: boolean
  class?: string
  formatter?: (value: any, row: any) => string
}

interface Action {
  label: string
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
}

const props = withDefaults(defineProps<Props>(), {
  actions: () => [],
  loading: false,
  title: undefined,
  emptyMessage: 'No data available',
  searchable: false,
})

const emit = defineEmits<{
  refresh: []
}>()

const UButton = resolveComponent('UButton')

// State
const searchQuery = ref('')

// Computed
const filteredData = computed(() => {
  if (!props.searchable || !searchQuery.value.trim()) {
    return props.data
  }

  const query = searchQuery.value.toLowerCase()
  return props.data.filter((item) => {
    return props.columns.some((column) => {
      const value = item[column.key]
      return String(value).toLowerCase().includes(query)
    })
  })
})

const hasActions = computed(() => props.actions.length > 0)

// Convert our column format to UTable format
const tableColumns = computed<TableColumn<any>[]>(() => {
  const cols: TableColumn<any>[] = props.columns.map(col => ({
    accessorKey: col.key,
    header: col.label,
    cell: ({ row }) => {
      const value = row.getValue(col.key)
      return col.formatter ? col.formatter(value, row.original) : value
    },
    meta: {
      class: {
        td: col.class,
      },
    },
  }))

  // Add actions column if we have actions
  if (hasActions.value) {
    cols.push({
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        return h(
          'div',
          { class: 'flex items-center gap-2' },
          props.actions
            .filter(action => action.show ? action.show(row.original) : true)
            .map(action =>
              h(UButton, {
                key: action.label,
                variant: action.variant || 'ghost',
                color: action.color || 'neutral',
                size: action.size || 'sm',
                icon: action.icon,
                onClick: () => action.handler(row.original),
              }, () => action.label),
            ),
        )
      },
      meta: {
        class: {
          th: 'w-32', // Fixed width for actions header
          td: 'w-32', // Fixed width for actions cells
        },
      },
    })
  }

  return cols
})

// Methods
function handleRefresh() {
  emit('refresh')
}
</script>

<template>
  <div class="rounded-xl border border-neutral-200 dark:border-neutral-800 overflow-hidden">
    <!-- Table Header -->
    <div v-if="title || searchable" class="px-4 py-2 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900">
      <div class="flex justify-between items-center">
        <div>
          <h3 v-if="title" class="text-sm font-semibold text-neutral-700 dark:text-neutral-300 tracking-wide">
            {{ title }}
          </h3>
        </div>
        <div class="flex items-center gap-2">
          <!-- Search -->
          <UInput
            v-if="searchable"
            v-model="searchQuery"
            placeholder="Search..."
            icon="i-lucide-search"
            size="sm"
            variant="ghost"
            class="w-56"
          />
          <!-- Refresh Button -->
          <UButton
            variant="ghost"
            color="neutral"
            icon="i-lucide-refresh-cw"
            size="sm"
            :loading="loading"
            @click="handleRefresh"
          />
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && filteredData.length === 0" class="p-6">
      <BaseEmptyState
        :title="searchQuery ? 'No results found' : 'No data available'"
        :message="searchQuery ? `No items match &quot;${searchQuery}&quot;` : emptyMessage"
        :icon="searchQuery ? 'i-lucide-search-x' : 'i-lucide-folder-open'"
        :action-label="undefined"
        :action-to="props.actionTo"
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
    >
      <!-- Forward all dynamic slots to UTable -->
      <template v-for="(_, slotName) in $slots" :key="slotName" #[slotName]="slotProps">
        <slot :name="slotName" v-bind="slotProps" />
      </template>
    </UTable>
  </div>
</template>
