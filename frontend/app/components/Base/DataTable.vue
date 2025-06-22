<script setup lang="ts">
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
  selectable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  actions: () => [],
  loading: false,
  title: undefined,
  emptyMessage: 'No data available',
  searchable: false,
  selectable: false,
})

const emit = defineEmits<{
  refresh: []
  selectionChange: [items: any[]]
}>()

// State
const searchQuery = ref('')
const selectedItems = ref<any[]>([])

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

// Methods
function handleRefresh() {
  emit('refresh')
}

function handleSelectionChange(items: any[]) {
  selectedItems.value = items
  emit('selectionChange', items)
}

function getCellValue(item: any, column: Column) {
  const value = item[column.key]
  return column.formatter ? column.formatter(value, item) : value
}

function isActionVisible(action: Action, item: any): boolean {
  return action.show ? action.show(item) : true
}

function toggleItemSelection(item: any, selected: boolean) {
  if (selected) {
    if (!selectedItems.value.includes(item)) {
      selectedItems.value.push(item)
    }
  }
  else {
    const index = selectedItems.value.indexOf(item)
    if (index > -1) {
      selectedItems.value.splice(index, 1)
    }
  }
  emit('selectionChange', selectedItems.value)
}
</script>

<template>
  <div class="bg-white rounded-lg shadow">
    <!-- Table Header -->
    <div v-if="title || searchable" class="px-6 py-4 border-b border-neutral-200">
      <div class="flex justify-between items-center">
        <div>
          <h3 v-if="title" class="text-lg font-medium text-neutral-900">
            {{ title }}
          </h3>
        </div>
        <div class="flex items-center gap-3">
          <!-- Search -->
          <UInput
            v-if="searchable"
            v-model="searchQuery"
            placeholder="Search..."
            icon="i-lucide-search"
            size="sm"
            class="w-64"
          />
          <!-- Refresh Button -->
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-refresh-cw"
            size="sm"
            :loading="loading"
            @click="handleRefresh"
          >
            Refresh
          </UButton>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="p-6">
      <BaseLoadingState message="Loading data..." />
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredData.length === 0" class="p-6">
      <BaseEmptyState
        :title="searchQuery ? 'No results found' : 'No data available'"
        :message="searchQuery ? `No items match &quot;${searchQuery}&quot;` : emptyMessage"
        :icon="searchQuery ? 'i-lucide-search-x' : 'i-lucide-folder-open'"
        :action-label="undefined"
      />
    </div>

    <!-- Data Table -->
    <div v-else class="overflow-x-auto">
      <table class="min-w-full divide-y divide-neutral-200">
        <!-- Table Header -->
        <thead class="bg-neutral-50">
          <tr>
            <!-- Selection Column -->
            <th v-if="selectable" class="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              <UCheckbox
                :model-value="selectedItems.length === filteredData.length"
                :indeterminate="selectedItems.length > 0 && selectedItems.length < filteredData.length"
                @update:model-value="handleSelectionChange($event ? filteredData : [])"
              />
            </th>
            <!-- Data Columns -->
            <th
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider"
              :class="column.class"
            >
              {{ column.label }}
            </th>
            <!-- Actions Column -->
            <th v-if="hasActions" class="relative px-6 py-3">
              <span class="sr-only">Actions</span>
            </th>
          </tr>
        </thead>

        <!-- Table Body -->
        <tbody class="bg-white divide-y divide-neutral-200">
          <tr v-for="(item, index) in filteredData" :key="index" class="hover:bg-neutral-50">
            <!-- Selection Column -->
            <td v-if="selectable" class="px-6 py-4 whitespace-nowrap">
              <UCheckbox
                :model-value="selectedItems.includes(item)"
                @update:model-value="toggleItemSelection(item, !!$event)"
              />
            </td>
            <!-- Data Columns -->
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-4 whitespace-nowrap text-sm text-neutral-900"
              :class="column.class"
            >
              <slot :name="`cell-${column.key}`" :item="item" :value="getCellValue(item, column)">
                {{ getCellValue(item, column) }}
              </slot>
            </td>
            <!-- Actions Column -->
            <td v-if="hasActions" class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <div class="flex items-center justify-end gap-2">
                <UButton
                  v-for="action in actions.filter(a => isActionVisible(a, item))"
                  :key="action.label"
                  :variant="action.variant || 'ghost'"
                  :color="action.color || 'neutral'"
                  :size="action.size || 'sm'"
                  :icon="action.icon"
                  @click="action.handler(item)"
                >
                  {{ action.label }}
                </UButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
