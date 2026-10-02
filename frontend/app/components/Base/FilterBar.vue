<script setup lang="ts">
import type { FilterDefinition, FilterEntry, FilterMode, FilterOption, FilterState, FilterValue } from '~/utils/filters'
import { effectiveMode, emptyFilterEntry, emptyFilterState, filterModes, modeLabel } from '~/utils/filters'

// Linear-style filters: a "Filter" button that opens a two-column picker, and one chip per active filter
// ("Provider · is any of · 3 providers · x") whose operator and values can each be changed in place.
const props = defineProps<{
  definitions: FilterDefinition[]
}>()
const filters = defineModel<FilterState>({ required: true })

const entryFor = (key: string): FilterEntry => filters.value[key] ?? emptyFilterEntry()
const selectedFor = (key: string) => entryFor(key).values

function selectedOptions(definition: FilterDefinition): FilterOption[] {
  const selected = selectedFor(definition.key)
  return definition.options.filter(option => selected.includes(option.value))
}

function toggle(definition: FilterDefinition, value: FilterValue) {
  const selected = selectedFor(definition.key)
  let next: FilterValue[]
  if (definition.multiple)
    next = selected.includes(value) ? selected.filter(item => item !== value) : [...selected, value]
  else
    // Single choice: picking the selected value again clears it
    next = selected.includes(value) ? [] : [value]
  // An emptied filter disappears, so it comes back as a plain "is" next time
  const mode = next.length ? entryFor(definition.key).mode : 'include'
  filters.value = { ...filters.value, [definition.key]: { mode, values: next } }
}

function setMode(definition: FilterDefinition, mode: FilterMode) {
  filters.value = { ...filters.value, [definition.key]: { ...entryFor(definition.key), mode } }
}

function remove(definition: FilterDefinition) {
  filters.value = { ...filters.value, [definition.key]: emptyFilterEntry() }
}

function clearAll() {
  filters.value = emptyFilterState(props.definitions)
}

const activeDefinitions = computed(() => props.definitions.filter(definition => selectedFor(definition.key).length))

// Column shown on the right of the "Filter" picker; follows hover and focus
const panelKey = ref(props.definitions[0]?.key)
const panelDefinition = computed(() => props.definitions.find(definition => definition.key === panelKey.value) ?? props.definitions[0]!)

function operator(definition: FilterDefinition) {
  const entry = entryFor(definition.key)
  return modeLabel(effectiveMode(entry), entry.values.length)
}

// "is all of" only differs from "is any of" once two values are picked, so it is offered from then on
function modeOptions(definition: FilterDefinition): FilterOption[] {
  const count = selectedFor(definition.key).length
  return filterModes(definition)
    .filter(mode => mode !== 'all' || count > 1)
    .map(mode => ({ value: mode, label: modeLabel(mode, count) }))
}

// Two short labels read fine side by side ("Active, Inactive"); past that, a count is clearer
function valueLabel(definition: FilterDefinition) {
  const labels = selectedOptions(definition).map(option => option.label)
  if (labels.length === 1 || (labels.length === 2 && labels.join(', ').length <= 14))
    return labels.join(', ')
  return `${labels.length} ${definition.plural ?? 'values'}`
}

// Past three icons, the rest collapse into an ellipsis square
const CHIP_ICON_LIMIT = 3
const iconOptions = (definition: FilterDefinition) => selectedOptions(definition).filter(option => option.icon)
const chipIcons = (definition: FilterDefinition) => iconOptions(definition).slice(0, CHIP_ICON_LIMIT)
const hasMoreIcons = (definition: FilterDefinition) => iconOptions(definition).length > CHIP_ICON_LIMIT

const POPOVER_CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
const SEGMENT = 'inline-flex cursor-pointer items-center gap-1.5 rounded-sm px-1.5 transition-colors duration-150 ease-out hover:bg-accented/60 data-[state=open]:bg-accented/60'
</script>

<template>
  <div class="flex flex-wrap items-center gap-1">
    <!-- First in the row, so adding a chip never moves the button the picker is anchored to -->
    <UPopover :content="POPOVER_CONTENT" :ui="{ content: 'overflow-hidden' }">
      <UButton
        color="neutral"
        variant="ghost"
        size="xs"
        icon="i-lucide-list-filter"
        label="Filter"
      />

      <template #content>
        <div class="flex items-stretch">
          <div role="tablist" aria-orientation="vertical" class="flex w-36 shrink-0 flex-col border-e border-default p-1">
            <button
              v-for="definition in definitions"
              :key="definition.key"
              type="button"
              role="tab"
              :aria-selected="panelDefinition.key === definition.key"
              class="flex h-7 cursor-pointer items-center gap-2 rounded-sm px-1.5 text-left text-xs outline-none focus-visible:bg-elevated"
              :class="panelDefinition.key === definition.key ? 'bg-elevated text-highlighted' : 'text-muted'"
              @pointerenter="panelKey = definition.key"
              @focus="panelKey = definition.key"
              @click="panelKey = definition.key"
            >
              <UIcon :name="definition.icon" class="size-3.5 shrink-0" aria-hidden="true" />
              <span class="flex-1 truncate">{{ definition.label }}</span>
              <span v-if="selectedFor(definition.key).length" class="text-xs text-dimmed tabular-nums">{{ selectedFor(definition.key).length }}</span>
            </button>
          </div>
          <BaseFilterOptionList
            :key="panelDefinition.key"
            role="tabpanel"
            class="w-48"
            :options="panelDefinition.options"
            :selected="selectedFor(panelDefinition.key)"
            :multiple="panelDefinition.multiple"
            :search-placeholder="panelDefinition.searchPlaceholder"
            @toggle="toggle(panelDefinition, $event)"
          />
        </div>
      </template>
    </UPopover>

    <div
      v-for="definition in activeDefinitions"
      :key="definition.key"
      class="inline-flex h-7 shrink-0 items-stretch gap-0.5 rounded-md bg-elevated p-0.5 text-xs whitespace-nowrap"
    >
      <!-- What is filtered, and how -->
      <span class="inline-flex items-center gap-1.5 ps-1.5 text-muted">
        <UIcon :name="definition.icon" class="size-3.5" aria-hidden="true" />
        {{ definition.label }}
      </span>
      <UPopover v-if="modeOptions(definition).length > 1" :content="POPOVER_CONTENT">
        <button
          type="button"
          class="font-semibold text-muted hover:text-highlighted data-[state=open]:text-highlighted"
          :class="SEGMENT"
          :aria-label="`Change ${definition.label} operator`"
        >
          {{ operator(definition) }}
          <UIcon name="i-lucide-chevron-down" class="size-3" aria-hidden="true" />
        </button>
        <template #content>
          <BaseFilterOptionList
            class="w-36"
            :options="modeOptions(definition)"
            :selected="[effectiveMode(entryFor(definition.key))]"
            @toggle="setMode(definition, $event as FilterMode)"
          />
        </template>
      </UPopover>
      <span v-else class="inline-flex items-center px-1.5 font-semibold text-muted">{{ operator(definition) }}</span>
      <span class="my-1 w-px bg-accented" aria-hidden="true" />
      <UPopover :content="POPOVER_CONTENT">
        <button
          type="button"
          class="font-medium text-highlighted"
          :class="SEGMENT"
          :aria-label="`Change ${definition.label} filter`"
        >
          <!-- Each logo sits on top of the one to its left; the white tile keeps black logos readable in dark mode -->
          <span v-if="chipIcons(definition).length" class="inline-flex items-center -space-x-1">
            <span
              v-for="option in chipIcons(definition)"
              :key="String(option.value)"
              class="relative inline-flex size-4 items-center justify-center rounded-sm border border-black/10 bg-white text-neutral-600"
            >
              <UIcon :name="option.icon!" class="size-2.5" />
            </span>
            <span
              v-if="hasMoreIcons(definition)"
              class="relative inline-flex size-4 items-center justify-center rounded-sm border border-black/10 bg-white text-neutral-500"
              aria-hidden="true"
            >
              <UIcon name="i-lucide-ellipsis" class="size-2.5" />
            </span>
          </span>
          {{ valueLabel(definition) }}
          <UIcon name="i-lucide-chevron-down" class="size-3 text-dimmed" aria-hidden="true" />
        </button>
        <template #content>
          <BaseFilterOptionList
            class="w-48"
            :options="definition.options"
            :selected="selectedFor(definition.key)"
            :multiple="definition.multiple"
            :search-placeholder="definition.searchPlaceholder"
            @toggle="toggle(definition, $event)"
          />
        </template>
      </UPopover>
      <span class="my-1 w-px bg-accented" aria-hidden="true" />
      <button
        type="button"
        class="inline-flex cursor-pointer items-center rounded-sm px-1.5 text-muted transition-colors duration-150 ease-out hover:bg-accented/60 hover:text-highlighted"
        :aria-label="`Remove ${definition.label} filter`"
        @click="remove(definition)"
      >
        <UIcon name="i-lucide-x" class="size-3.5" />
      </button>
    </div>

    <UButton
      v-if="activeDefinitions.length"
      color="neutral"
      variant="link"
      size="xs"
      label="Clear"
      class="text-muted"
      @click="clearAll"
    />
  </div>
</template>
