<script setup lang="ts">
// A titled block of an experiment page (the form, the results). Sections stack, separated by a rule.
defineProps<{
  id: string
  title: string
  description?: string
  /** Tighter rhythm, for sections in a side column */
  compact?: boolean
}>()

defineSlots<{
  default?: any
  actions?: any
}>()
</script>

<template>
  <section
    :id="id"
    :aria-labelledby="`${id}-title`"
    class="scroll-mt-6 border-t border-default first:border-t-0 first:pt-0"
    :class="compact ? 'pt-5' : 'pt-8'"
  >
    <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div class="min-w-0">
        <h2 :id="`${id}-title`" class="text-base font-semibold text-highlighted">
          {{ title }}
        </h2>
        <p v-if="description" class="mt-0.5 max-w-prose text-sm text-muted text-pretty">
          {{ description }}
        </p>
      </div>
      <div v-if="$slots.actions" class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <div :class="compact ? 'mt-3' : 'mt-4'">
      <slot />
    </div>
  </section>
</template>
