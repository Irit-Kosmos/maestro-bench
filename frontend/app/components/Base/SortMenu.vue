<script setup lang="ts" generic="T">
import type { FilterOption, FilterValue } from '~/utils/filters'
import type { SortDirection, SortSpec, SortState } from '~/utils/sorts'
import { activeSortSpec, pickSort } from '~/utils/sorts'

// The "Sort" button of a list and its menu: what to sort on, and which way. Sits next to "Filter" and "Group".
const props = defineProps<{
  sorts: SortSpec<T>[]
}>()
const sortBy = defineModel<SortState | null>({ default: null })

const open = ref(false)
const active = computed(() => activeSortSpec(props.sorts, sortBy.value))

// '' stands for "No sorting", like in the group menu
const options = computed<FilterOption[]>(() => [
  { value: '', label: 'No sorting', icon: 'i-ph-x-bold' },
  ...props.sorts.map(spec => ({ value: spec.key, label: spec.label, icon: spec.icon })),
])

const DIRECTIONS: { value: SortDirection, label: string, icon: string }[] = [
  { value: 'asc', label: 'Ascending', icon: 'i-ph-arrow-up-bold' },
  { value: 'desc', label: 'Descending', icon: 'i-ph-arrow-down-bold' },
]

const direction = computed(() => active.value ? sortBy.value!.direction : null)

function pick(value: FilterValue) {
  const spec = props.sorts.find(found => found.key === value)
  sortBy.value = spec ? pickSort(spec, sortBy.value) : null
  // Nothing left to set once the sorting is off; otherwise the menu stays, to flip the direction and watch the list move
  if (!spec)
    open.value = false
}

function setDirection(next: SortDirection) {
  if (active.value)
    sortBy.value = { key: active.value.key, direction: next }
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ align: 'start', sideOffset: 6, collisionPadding: 16 }">
    <UButton
      color="neutral"
      variant="ghost"
      size="xs"
      :icon="direction === 'asc' ? 'i-ph-sort-ascending-bold' : direction === 'desc' ? 'i-ph-sort-descending-bold' : 'i-ph-arrows-down-up-bold'"
      :label="active ? `Sort: ${active.label}` : 'Sort'"
      :aria-label="active ? `Sorted by ${active.label}, ${direction === 'asc' ? 'ascending' : 'descending'}` : 'Sort'"
    />
    <template #content>
      <div class="flex w-52 flex-col">
        <!-- Which way; it has nothing to turn while no sorting is picked -->
        <div role="group" aria-label="Sort direction" class="flex shrink-0 gap-0.5 border-b border-default p-1">
          <button
            v-for="item in DIRECTIONS"
            :key="item.value"
            type="button"
            :disabled="!active"
            :aria-pressed="direction === item.value"
            class="flex h-7 flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-sm text-xs outline-none transition-colors duration-150 ease-out focus-visible:bg-elevated disabled:pointer-events-none disabled:opacity-40"
            :class="direction === item.value ? 'bg-elevated font-medium text-highlighted' : 'text-muted hover:bg-elevated/60 hover:text-highlighted'"
            @click="setDirection(item.value)"
          >
            <UIcon :name="item.icon" class="size-3.5" aria-hidden="true" />
            {{ item.label }}
          </button>
        </div>
        <BaseFilterOptionList
          :options="options"
          :selected="[active?.key ?? '']"
          @toggle="pick"
        />
      </div>
    </template>
  </UPopover>
</template>
