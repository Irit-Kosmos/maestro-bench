<script setup lang="ts">
import type { FilterOption, FilterValue } from '~/utils/filters'

// The options of one filter: checkboxes when several can be picked, radios otherwise, with an optional search
const props = withDefaults(defineProps<{
  options: FilterOption[]
  selected: FilterValue[]
  multiple?: boolean
  searchPlaceholder?: string
}>(), {
  multiple: false,
})

const emit = defineEmits<{
  toggle: [value: FilterValue]
}>()

const search = ref('')

const visibleOptions = computed(() => {
  const term = search.value.trim().toLowerCase()
  return term ? props.options.filter(option => option.label.toLowerCase().includes(term)) : props.options
})

const isSelected = (option: FilterOption) => props.selected.includes(option.value)
</script>

<template>
  <div class="flex flex-col">
    <input
      v-if="searchPlaceholder"
      v-model="search"
      type="text"
      :placeholder="searchPlaceholder"
      :aria-label="searchPlaceholder"
      class="h-8 w-full shrink-0 border-0 border-b border-default bg-transparent px-2.5 text-xs text-highlighted outline-none placeholder:text-dimmed"
    >
    <div role="group" class="flex max-h-64 min-h-0 flex-1 flex-col overflow-y-auto p-1">
      <button
        v-for="option in visibleOptions"
        :key="String(option.value)"
        type="button"
        :role="multiple ? 'menuitemcheckbox' : 'menuitemradio'"
        :aria-checked="isSelected(option)"
        class="flex h-7 w-full shrink-0 cursor-pointer items-center gap-2 rounded-sm px-1.5 text-left text-xs text-default outline-none hover:bg-elevated focus-visible:bg-elevated"
        @click="emit('toggle', option.value)"
      >
        <span
          v-if="multiple"
          class="flex size-3.5 shrink-0 items-center justify-center rounded-xs border"
          :class="isSelected(option) ? 'border-inverted bg-inverted text-inverted' : 'border-accented'"
          aria-hidden="true"
        >
          <UIcon v-if="isSelected(option)" name="i-lucide-check" class="size-2.5" />
        </span>
        <!-- Ring and dot in one SVG: a CSS border snaps to device pixels but its content does not,
             so a dot nested in a bordered box drifts off-center at fractional positions -->
        <svg
          v-else
          viewBox="0 0 14 14"
          class="size-3.5 shrink-0 overflow-visible"
          :class="isSelected(option) ? 'text-highlighted' : 'text-accented'"
          aria-hidden="true"
        >
          <circle cx="7" cy="7" r="6.5" :fill="isSelected(option) ? 'currentColor' : 'none'" stroke="currentColor" />
          <circle v-if="isSelected(option)" cx="7" cy="7" r="3" class="fill-(--ui-bg)" />
        </svg>
        <UIcon v-if="option.icon" :name="option.icon" class="size-3.5 shrink-0" :class="option.iconClass" aria-hidden="true" />
        <span class="flex-1 truncate">{{ option.label }}</span>
        <span v-if="option.count !== undefined" class="text-xs text-dimmed tabular-nums">{{ option.count }}</span>
      </button>
      <span v-if="!visibleOptions.length" class="px-1.5 py-2 text-xs text-muted">No match</span>
    </div>
  </div>
</template>
