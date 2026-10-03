<script setup lang="ts">
// A row that opens something: one link across the whole row, so the hit area is the row
defineProps<{ to: string }>()
</script>

<template>
  <!-- Hover is instant on purpose: rows are scanned and hovered constantly -->
  <NuxtLink
    :to="to"
    class="flex items-center gap-3 h-11 px-4 outline-none hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
  >
    <slot />
  </NuxtLink>
</template>
