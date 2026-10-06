<script setup lang="ts">
import type { FilterOption, FilterValue } from '~/utils/filters'

// The "Group" button of a list and its menu: what to cut the rows into sections by. Sits next to "Filter" and "Sort".
const props = defineProps<{
  /** The ways to group, an entry of the menu each */
  groups: { key: string, label: string, icon: string }[]
}>()
const groupBy = defineModel<string | null>({ default: null })

const open = ref(false)
const active = computed(() => props.groups.find(group => group.key === groupBy.value) ?? null)

// Same option list as the filters; '' stands for "No grouping"
const options = computed<FilterOption[]>(() => [
  { value: '', label: 'No grouping', icon: 'i-ph-x-bold' },
  ...props.groups.map(group => ({ value: group.key, label: group.label, icon: group.icon })),
])

function pick(value: FilterValue) {
  groupBy.value = value === '' ? null : String(value)
  open.value = false
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ align: 'start', sideOffset: 6, collisionPadding: 16 }">
    <UButton
      color="neutral"
      variant="ghost"
      size="xs"
      icon="i-ph-rows-bold"
      :label="active ? `Group: ${active.label}` : 'Group'"
    />
    <template #content>
      <BaseFilterOptionList
        class="w-44"
        :options="options"
        :selected="[active?.key ?? '']"
        @toggle="pick"
      />
    </template>
  </UPopover>
</template>
