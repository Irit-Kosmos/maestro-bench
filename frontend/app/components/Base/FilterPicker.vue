<script setup lang="ts">
import type { FilterDefinition, FilterState } from '~/utils/filters'

// The "Filter" button and its two-column picker: categories on the left, their options on the right.
// `compact` draws it as a bare "+", to add a filter from the row of chips.
const props = defineProps<{
  definitions: FilterDefinition[]
  compact?: boolean
}>()
const filters = defineModel<FilterState>({ required: true })

const { selectedFor, toggle } = useFilterEditing(filters, () => props.definitions)

// Column shown on the right of the picker; follows hover and focus
const panelKey = ref(props.definitions[0]?.key)
const panelDefinition = computed(() => props.definitions.find(definition => definition.key === panelKey.value) ?? props.definitions[0]!)

const { containerEl: pickerEl, listEl: tabListEl, select: showPanel, onEnter: hoverTab, onMove: moveInTabs, onLeave: leaveTabs } = useSafeTriangle(panelKey)

// Roving tabindex: only the shown tab is a tab stop, so Tab leaves for the options and the arrows move between categories
function onTabKeydown(event: KeyboardEvent) {
  const tabs = Array.from(tabListEl.value?.querySelectorAll<HTMLElement>('[role="tab"]') ?? [])
  const index = tabs.findIndex(tab => tab === event.target)
  if (index === -1)
    return
  const last = tabs.length - 1
  const targets: Record<string, number> = {
    ArrowDown: index === last ? 0 : index + 1,
    ArrowUp: index === 0 ? last : index - 1,
    Home: 0,
    End: last,
  }
  const target = targets[event.key]
  if (target === undefined)
    return
  event.preventDefault()
  // Focusing the tab also shows its panel
  tabs[target]?.focus()
}
</script>

<template>
  <UPopover
    :content="{ align: 'start', sideOffset: 6, collisionPadding: 16 }"
    :ui="{ content: 'max-w-[calc(100vw-2rem)] overflow-hidden' }"
  >
    <UButton
      v-if="compact"
      color="neutral"
      variant="ghost"
      size="xs"
      icon="i-ph-plus-bold"
      aria-label="Add filter"
      class="text-muted active:scale-100!"
    />
    <UButton
      v-else
      color="neutral"
      variant="ghost"
      size="xs"
      icon="i-ph-funnel-simple-bold"
      label="Filter"
      class="active:scale-100!"
    />

    <template #content>
      <div ref="pickerEl" class="flex items-stretch">
        <div
          ref="tabListEl"
          role="tablist"
          aria-orientation="vertical"
          class="flex min-h-72 w-36 shrink-0 flex-col border-e border-default p-1"
          @pointermove="moveInTabs"
          @pointerleave="leaveTabs"
          @keydown="onTabKeydown"
        >
          <button
            v-for="definition in definitions"
            :key="definition.key"
            type="button"
            role="tab"
            :aria-selected="panelDefinition.key === definition.key"
            :tabindex="panelDefinition.key === definition.key ? 0 : -1"
            class="flex h-7 cursor-pointer items-center gap-2 rounded-sm px-1.5 text-start text-xs outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
            :class="panelDefinition.key === definition.key ? 'bg-elevated text-highlighted' : 'text-muted'"
            @pointerenter="hoverTab(definition.key, $event)"
            @focus="showPanel(definition.key)"
            @click="showPanel(definition.key)"
          >
            <UIcon :name="definition.icon" class="size-3.5 shrink-0" aria-hidden="true" />
            <span class="flex-1 truncate">{{ definition.label }}</span>
            <span v-if="selectedFor(definition.key).length" class="text-xs text-muted tabular-nums">{{ selectedFor(definition.key).length }}</span>
          </button>
        </div>
        <!-- Out of the flow, so the tab list alone sets the height and long option lists scroll -->
        <div class="relative w-48 min-w-0">
          <BaseFilterOptionList
            :key="panelDefinition.key"
            role="tabpanel"
            class="absolute inset-0"
            :options="panelDefinition.options"
            :selected="selectedFor(panelDefinition.key)"
            :multiple="panelDefinition.multiple"
            :search-placeholder="panelDefinition.searchPlaceholder"
            @toggle="toggle(panelDefinition, $event)"
          />
        </div>
      </div>
    </template>
  </UPopover>
</template>
