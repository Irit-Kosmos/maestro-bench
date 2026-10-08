<script setup lang="ts">
import type { FilterOption, FilterValue } from '~/utils/filters'
import { useResizeObserver } from '@vueuse/core'

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

// A fade at the foot of a long list says there is more below; it goes once the end is reached
const list = useTemplateRef<HTMLElement>('list')
const moreBelow = ref(false)
function measure() {
  const el = list.value
  moreBelow.value = !!el && el.scrollHeight - el.scrollTop - el.clientHeight > 4
}
useResizeObserver(list, measure)
watch(visibleOptions, () => nextTick(measure))

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
    <div class="relative flex min-h-0 flex-1 flex-col">
      <div ref="list" role="group" class="flex max-h-64 min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain p-1" @scroll.passive="measure">
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
            <UIcon v-if="isSelected(option)" name="i-ph-check-bold" class="size-2.5" />
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
          <span v-else-if="option.dot" class="size-2 shrink-0 rounded-full" :class="option.dot" aria-hidden="true" />
          <span class="flex-1 truncate">{{ option.label }}</span>
          <span v-if="option.count !== undefined" class="text-xs text-dimmed tabular-nums">{{ option.count }}</span>
        </button>
        <span v-if="!visibleOptions.length" class="px-1.5 py-2 text-xs text-muted">No match</span>
      </div>
      <div
        class="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-(--ui-bg) to-transparent transition-opacity duration-150"
        :class="moreBelow ? 'opacity-100' : 'opacity-0'"
        aria-hidden="true"
      />
    </div>
  </div>
</template>
