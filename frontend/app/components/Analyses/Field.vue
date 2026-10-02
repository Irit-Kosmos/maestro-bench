<script setup lang="ts">
// One line of the analysis settings: what it is on the left, its control on the right
defineProps<{
  label: string
  hint?: string
  required?: boolean
}>()

defineSlots<{ default?: any }>()

const labelId = useId()
</script>

<template>
  <div role="group" :aria-labelledby="labelId" class="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
    <div class="min-w-0">
      <p :id="labelId" class="text-sm text-highlighted">
        {{ label }}<span v-if="required" class="text-error" aria-hidden="true"> *</span>
      </p>
      <p v-if="hint" class="text-xs text-muted text-pretty">
        {{ hint }}
      </p>
    </div>
    <div class="flex min-w-0 flex-wrap gap-1.5 sm:justify-end">
      <slot />
    </div>
  </div>
</template>
