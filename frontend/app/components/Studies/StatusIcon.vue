<script setup lang="ts">
// A study's status as an icon: each has its own shape, so it still reads without colour
const props = withDefaults(defineProps<{
  status: string
  /** Tailwind size class of the icon */
  size?: string
  /** Rich tooltip with the status in words, instead of the native title */
  tooltip?: boolean
}>(), {
  size: 'size-3.5',
  tooltip: false,
})

const meta = computed(() => studyStatusMeta(props.status))
</script>

<template>
  <UTooltip :text="`${meta.label}: ${meta.description}`" :disabled="!tooltip">
    <span class="inline-flex shrink-0 items-center align-middle" :title="tooltip ? undefined : meta.label">
      <UIcon :name="meta.icon" :class="[size, meta.tone]" aria-hidden="true" />
      <span class="sr-only">{{ meta.label }}</span>
    </span>
  </UTooltip>
</template>
