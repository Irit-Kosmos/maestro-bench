<script setup lang="ts">
import type { Prompt } from '~/types'
import type { FilterSpec } from '~/utils/filters'
import { dateFilter } from '~/utils/filterSpecs'

interface Props {
  data: Prompt[]
  loading?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  refresh: []
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Prompt',
  },
  {
    key: 'category',
    label: 'Category',
  },
  {
    key: 'description',
    label: 'Description',
  },
  {
    key: 'created_at',
    label: 'Created',
  },
]

const filters: FilterSpec<Prompt>[] = [
  {
    key: 'category',
    label: 'Category',
    icon: 'i-lucide-tag',
    plural: 'categories',
    searchPlaceholder: 'Search a category…',
    value: prompt => prompt.category,
  },
  dateFilter(prompt => prompt.created_at),
]
</script>

<template>
  <BaseDataTable
    :data="data"
    :columns="columns"
    :filters="filters"
    :loading="loading"
    :row-to="(prompt: Prompt) => `/prompts/${prompt.id}`"
    item-name="prompt"
    searchable
    @refresh="emit('refresh')"
  >
    <!-- Custom cell for category -->
    <template #category-cell="{ row }">
      <UBadge
        v-if="row.original.category"
        color="neutral"
        variant="soft"
      >
        {{ row.original.category }}
      </UBadge>
      <span v-else class="text-dimmed text-sm">—</span>
    </template>

    <!-- Custom cell for created_at -->
    <template #created_at-cell="{ row }">
      <span class="text-sm text-muted tabular-nums" :title="formatDate(row.original.created_at)">
        {{ formatRelativeDate(row.original.created_at) }}
      </span>
    </template>

    <!-- Custom cell for description -->
    <template #description-cell="{ row }">
      <span class="block max-w-md truncate text-sm text-toned" :title="row.original.description || undefined">
        {{ row.original.description || '—' }}
      </span>
    </template>
  </BaseDataTable>
</template>
