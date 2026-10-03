<script setup lang="ts">
// One bar per slice of the period, tallest where the figure peaks. The card carries the figure
// itself: the bars are there to be hovered, each naming its slice at once (no delay, the first
// tooltip of a sweep included). The color is the text's.
const props = defineProps<{
  values: readonly number[]
  /** What each bar stands for, in the same order as `values` */
  labels?: readonly string[]
}>()

const bars = computed(() => {
  const peak = Math.max(...props.values, 0)
  return props.values.map((value, i) => ({
    // Slices with nothing keep a hairline, so the time axis stays visible
    height: value > 0 ? `${Math.max(8, (value / peak) * 100)}%` : '1px',
    empty: value <= 0,
    label: props.labels?.[i],
  }))
})
</script>

<template>
  <div v-if="values.length" class="flex h-7 w-24 shrink-0 items-stretch gap-px" aria-hidden="true">
    <UTooltip
      v-for="(bar, i) in bars"
      :key="i"
      :text="bar.label"
      :disabled="!bar.label"
      :delay-duration="0"
      :content="{ side: 'top', sideOffset: 4 }"
    >
      <div class="group flex min-w-0 flex-1 items-end rounded-xs hover:bg-elevated">
        <div
          class="w-full rounded-[1px] bg-current"
          :class="bar.empty ? 'opacity-25' : 'group-hover:opacity-70'"
          :style="{ height: bar.height }"
        />
      </div>
    </UTooltip>
  </div>
</template>
