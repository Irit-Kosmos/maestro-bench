<script setup lang="ts">
// One fact in a page's meta line: a quiet icon, then the value
defineProps<{
  icon: string
  /** Names the fact for assistive tech and on hover, since the icon alone doesn't */
  label: string
}>()
</script>

<template>
  <span class="inline-flex min-w-0 items-center gap-1.5" :title="label">
    <UIcon :name="icon" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
    <span class="sr-only">{{ label }}: </span>
    <slot />
  </span>
</template>
