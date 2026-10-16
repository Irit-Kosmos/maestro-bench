<script setup lang="ts" generic="T">
import type { SortSpec, SortState } from '~/utils/sorts'
import { activeSortSpec, pickSort } from '~/utils/sorts'

// The "Display" button of a list and its panel: how the rows are grouped and ordered.
// One button of a fixed width, so picking a grouping or a sort never moves the toolbar; what is picked shows in the panel.
const props = withDefaults(defineProps<{
  /** The ways to group; the row is left out without any */
  groups?: { key: string, label: string, icon: string }[]
  /** The things to sort on; the row is left out without any */
  sorts?: SortSpec<T>[]
}>(), {
  groups: () => [],
  sorts: () => [],
})
const groupBy = defineModel<string | null>('groupBy', { default: null })
const sortBy = defineModel<SortState | null>('sortBy', { default: null })

// A select can't hold an empty value, so "none" stands for no grouping and no sorting
const NONE = 'none'

const groupItems = computed(() => [
  { value: NONE, label: 'No grouping', icon: 'i-ph-minus-bold' },
  ...props.groups.map(group => ({ value: group.key, label: group.label, icon: group.icon })),
])
const sortItems = computed(() => [
  { value: NONE, label: 'No sorting', icon: 'i-ph-minus-bold' },
  ...props.sorts.map(spec => ({ value: spec.key, label: spec.label, icon: spec.icon })),
])

const activeGroup = computed(() => props.groups.find(group => group.key === groupBy.value) ?? null)
const activeSort = computed(() => activeSortSpec(props.sorts, sortBy.value))

const groupValue = computed({
  get: () => activeGroup.value?.key ?? NONE,
  set: (value: string) => { groupBy.value = value === NONE ? null : value },
})
const sortValue = computed({
  get: () => activeSort.value?.key ?? NONE,
  set: (value: string) => {
    const spec = props.sorts.find(found => found.key === value)
    sortBy.value = spec ? pickSort(spec, sortBy.value) : null
  },
})

const direction = computed(() => activeSort.value ? sortBy.value!.direction : null)

function flipDirection() {
  if (activeSort.value)
    sortBy.value = { key: activeSort.value.key, direction: direction.value === 'asc' ? 'desc' : 'asc' }
}

const summary = computed(() => [
  activeGroup.value && `grouped by ${activeGroup.value.label}`,
  activeSort.value && `sorted by ${activeSort.value.label}`,
].filter(Boolean).join(', '))

const ROW = 'flex items-center gap-2'
const LABEL = 'flex flex-1 items-center gap-2 text-xs text-muted'
</script>

<template>
  <UPopover :content="{ align: 'end', sideOffset: 6, collisionPadding: 16 }">
    <UButton
      color="neutral"
      variant="ghost"
      size="xs"
      icon="i-ph-sliders-horizontal-bold"
      label="Display"
      :aria-label="summary ? `Display, ${summary}` : 'Display'"
      class="active:scale-100!"
    />

    <template #content>
      <div class="flex w-72 flex-col gap-2 p-3">
        <div v-if="groups.length" :class="ROW">
          <span :class="LABEL">
            <UIcon name="i-ph-rows-bold" class="size-3.5" aria-hidden="true" />
            Grouping
          </span>
          <USelect
            v-model="groupValue"
            :items="groupItems"
            size="xs"
            class="w-40"
            aria-label="Grouping"
          />
        </div>

        <div v-if="sorts.length" :class="ROW">
          <span :class="LABEL">
            <UIcon name="i-ph-arrows-down-up-bold" class="size-3.5" aria-hidden="true" />
            Ordering
          </span>
          <!-- Narrower than the grouping select by the direction button, so both end on the same edge -->
          <USelect
            v-model="sortValue"
            :items="sortItems"
            size="xs"
            class="w-32"
            aria-label="Ordering"
          />
          <UTooltip :text="direction === 'desc' ? 'Descending' : 'Ascending'">
            <UButton
              color="neutral"
              variant="outline"
              size="xs"
              square
              :icon="direction === 'desc' ? 'i-ph-sort-descending-bold' : 'i-ph-sort-ascending-bold'"
              :disabled="!activeSort"
              :aria-label="direction === 'desc' ? 'Descending, switch to ascending' : 'Ascending, switch to descending'"
              @click="flipDirection"
            />
          </UTooltip>
        </div>
      </div>
    </template>
  </UPopover>
</template>
