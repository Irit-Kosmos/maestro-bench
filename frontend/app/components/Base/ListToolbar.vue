<script setup lang="ts">
import type { FilterDefinition, FilterState } from '~/utils/filters'

// The toolbar of a list: search, filters, then the count and a refresh button.
// What is specific to a list goes in the slots: `default` right after the filters, `trailing` before the count.
const props = withDefaults(defineProps<{
  definitions: FilterDefinition[]
  /** Items before any search or filter, and how many are left */
  total: number
  shown: number
  /** Noun used in the count, e.g. "model" -> "12 models" */
  itemName?: string
  itemNamePlural?: string
  /** Shown instead of the search box when the list can't be searched */
  title?: string
  searchable?: boolean
  loading?: boolean
}>(), {
  itemName: undefined,
  itemNamePlural: undefined,
  title: undefined,
  searchable: true,
  loading: false,
})

const emit = defineEmits<{
  refresh: []
}>()

const search = defineModel<string>('search', { default: '' })
const filters = defineModel<FilterState>('filters', { required: true })

const searchInput = useTemplateRef<{ inputRef: HTMLInputElement | null }>('searchInput')
defineShortcuts({
  '/': () => searchInput.value?.inputRef?.focus(),
})

const plural = computed(() => props.itemNamePlural ?? (props.itemName ? `${props.itemName}s` : undefined))

const countLabel = computed(() => {
  if (!props.itemName)
    return ''
  const noun = props.total === 1 ? props.itemName : plural.value
  return props.shown === props.total ? `${props.total} ${noun}` : `${props.shown} of ${props.total} ${noun}`
})
</script>

<template>
  <div class="flex min-h-11 shrink-0 flex-wrap items-center gap-x-1 gap-y-1 border-b border-default px-2 py-1">
    <UInput
      v-if="searchable"
      ref="searchInput"
      v-model="search"
      placeholder="Filter…"
      icon="i-lucide-search"
      size="sm"
      variant="none"
      :aria-label="`Filter ${plural ?? 'rows'}`"
      class="min-w-32 flex-1 sm:max-w-56"
      @keydown.esc="search = ''"
    >
      <template v-if="!search" #trailing>
        <UKbd value="/" size="sm" />
      </template>
    </UInput>
    <h3 v-else-if="title" class="px-2 text-sm font-medium text-highlighted">
      {{ title }}
    </h3>

    <BaseFilterBar v-if="definitions.length" v-model="filters" :definitions="definitions" />

    <slot />

    <span class="flex-1" />

    <slot name="trailing" />

    <span v-if="countLabel" class="ps-2 text-xs text-muted tabular-nums">{{ countLabel }}</span>
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
