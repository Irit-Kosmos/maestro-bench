<script setup lang="ts">
import type { Prompt } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { SortSpec } from '~/utils/sorts'
import { dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'
import { dateSort, nameSort, textSort } from '~/utils/sortSpecs'

interface Props {
  data: Prompt[]
  loading?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  refresh: []
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Prompt',
  },
  {
    key: 'tags',
    label: 'Tags',
    // What the search reads; the cell below shows the chips
    formatter: (_: unknown, prompt: Prompt) => prompt.tags.map(tag => tag.name).join(' '),
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
  tagsFilter<Prompt>(prompt => prompt.tags),
  dateFilter(prompt => prompt.created_at),
]

const sorts: SortSpec<Prompt>[] = [
  nameSort(prompt => prompt.name, 'Prompt'),
  textSort('description', 'Description', 'i-ph-text-align-left-bold', prompt => prompt.description),
  dateSort(prompt => prompt.created_at),
]

// Clicking a tag in a row filters the list on it
const filterState = ref<FilterState>({})
</script>

<template>
  <BaseDataTable
    v-model:filter-state="filterState"
    :data="data"
    :columns="columns"
    :filters="filters"
    :sorts="sorts"
    :loading="loading"
    :row-to="(prompt: Prompt) => `/prompts/${prompt.id}`"
    item-name="prompt"
    searchable
    :selectable="canEdit"
    @refresh="emit('refresh')"
  >
    <template #selection-actions="{ rows }">
      <TagsBulkMenu kind="prompt" :rows="rows" @changed="emit('refresh')" />
    </template>

    <template #tags-cell="{ row }">
      <TagsList :id="row.original.id" :tags="row.original.tags" kind="prompt" selectable @changed="emit('refresh')" @select="tag => { filterState = filterByTag(filterState, tag.name) }" />
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
