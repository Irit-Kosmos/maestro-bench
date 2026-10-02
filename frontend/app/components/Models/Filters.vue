<script setup lang="ts">
import type { ModelGroupBy } from '~/composables/useModelFilters'
import type { FilterDefinition, FilterState } from '~/utils/filters'

// The toolbar of the models list: search, filters, and how to group the rows
const props = defineProps<{
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

const searchInput = useTemplateRef<{ inputRef: HTMLInputElement | null }>('searchInput')
defineShortcuts({
  '/': () => searchInput.value?.inputRef?.focus(),
})

const groupItems = [
  { label: 'Group by provider', value: 'provider', icon: 'i-lucide-layers' },
  { label: 'Group by status', value: 'status', icon: 'i-lucide-list-checks' },
  { label: 'No grouping', value: 'none', icon: 'i-lucide-list' },
]

const countLabel = computed(() =>
  props.shown === props.total
    ? `${props.total} ${props.total === 1 ? 'model' : 'models'}`
    : `${props.shown} of ${props.total} models`,
)
</script>

<template>
  <div class="flex min-h-11 flex-wrap items-center gap-x-1 gap-y-1 border-b border-default px-2 py-1">
    <UInput
      ref="searchInput"
      v-model="search"
      placeholder="Filter…"
      icon="i-lucide-search"
      size="sm"
      variant="none"
      aria-label="Filter models"
      class="min-w-32 flex-1 sm:max-w-56"
      @keydown.esc="search = ''"
    >
      <template v-if="!search" #trailing>
        <UKbd value="/" size="sm" />
      </template>
    </UInput>

    <BaseFilterBar v-model="filters" :definitions="definitions" />

    <span class="flex-1" />

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

    <span class="ps-2 text-xs text-muted tabular-nums">{{ countLabel }}</span>
    <UTooltip text="Refresh">
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-lucide-refresh-cw"
        size="sm"
        aria-label="Refresh"
        :loading="loading"
        @click="emit('refresh')"
      />
    </UTooltip>
  </div>
</template>
