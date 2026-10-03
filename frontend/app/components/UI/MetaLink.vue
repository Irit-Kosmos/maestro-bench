<script setup lang="ts">
// A link inside a meta line: same colors as before, with an arrow that slides in on hover/focus
defineProps<{
  to: string
}>()
</script>

<template>
  <NuxtLink
    :to="to"
    class="group/link inline-flex min-w-0 items-center gap-1 rounded text-toned outline-none transition-colors hover:text-highlighted focus-visible:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
  >
    <span class="truncate underline-offset-2 group-hover/link:underline"><slot /></span>
    <UIcon
      name="i-ph-arrow-right-bold"
      class="size-3.5 shrink-0 -translate-x-1 text-toned opacity-0 transition duration-200 ease-out group-hover/link:translate-x-0 group-hover/link:opacity-100 group-focus-visible/link:translate-x-0 group-focus-visible/link:opacity-100 motion-reduce:transition-none"
      aria-hidden="true"
    />
  </NuxtLink>
</template>
