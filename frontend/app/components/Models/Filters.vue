<script setup lang="ts">
import type { ModelGroupBy } from '~/composables/useModelFilters'
import type { FilterDefinition, FilterState } from '~/utils/filters'

// The toolbar of the models list: the shared one, plus how to group the rows
defineProps<{
  definitions: FilterDefinition[]
  total: number
  shown: number
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

const search = defineModel<string>('search', { required: true })
const filters = defineModel<FilterState>('filters', { required: true })
const groupBy = defineModel<ModelGroupBy>('groupBy', { required: true })

const groupItems = [
  { label: 'Group by provider', value: 'provider', icon: 'i-lucide-layers' },
  { label: 'Group by status', value: 'status', icon: 'i-lucide-list-checks' },
  { label: 'No grouping', value: 'none', icon: 'i-lucide-list' },
]
</script>

<template>
  <BaseListToolbar
    v-model:search="search"
    v-model:filters="filters"
    :definitions="definitions"
    :total="total"
    :shown="shown"
    :loading="loading"
    item-name="model"
    @refresh="emit('refresh')"
  >
    <template #trailing>
      <USelectMenu
        v-model="groupBy"
        value-key="value"
        :items="groupItems"
        :search-input="false"
        size="xs"
        variant="ghost"
        color="neutral"
        class="w-40"
        aria-label="Group models"
      />
    </template>
  </BaseListToolbar>
</template>
