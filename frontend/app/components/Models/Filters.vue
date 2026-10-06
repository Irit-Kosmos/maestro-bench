<script setup lang="ts">
import type { FilterDefinition, FilterState } from '~/utils/filters'
import type { SortState } from '~/utils/sorts'
import { modelGroups, modelSorts } from '~/composables/useModelFilters'

// The toolbar of the models list: the shared one, with the same Group and Sort menus as the tables
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
const groupBy = defineModel<string | null>('groupBy', { required: true })
const sortBy = defineModel<SortState | null>('sortBy', { required: true })
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
    <template #group>
      <BaseGroupMenu v-model="groupBy" :groups="modelGroups" />
      <BaseSortMenu v-model="sortBy" :sorts="modelSorts" />
    </template>
  </BaseListToolbar>
</template>
