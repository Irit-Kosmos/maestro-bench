<script setup lang="ts">
// The frame every dashboard block shares: a title, an optional way to see the full list, a body
defineProps<{
  title: string
  /** Where "View all" goes; no link without it */
  to?: string
}>()

defineSlots<{
  /** Small status text, left of the link */
  meta?: any
  default?: any
}>()

const titleId = useId()
</script>

<template>
  <section :aria-labelledby="titleId" class="rounded-lg border border-default overflow-hidden">
    <header class="flex items-center justify-between gap-3 h-11 px-4 border-b border-default">
      <h2 :id="titleId" class="text-sm font-medium text-highlighted">
        {{ title }}
      </h2>
      <div class="flex items-center gap-3">
        <slot name="meta" />
        <UButton
          v-if="to"
          :to="to"
          color="neutral"
          variant="link"
          size="xs"
          trailing-icon="i-ph-arrow-right-bold"
          class="-me-1.5"
        >
          View all
        </UButton>
      </div>
    </header>
    <slot />
  </section>
</template>
