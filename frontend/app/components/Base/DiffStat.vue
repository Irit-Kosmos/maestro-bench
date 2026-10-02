<script setup lang="ts">
// "+12 −3": lines added and removed. Digits are tabular so the figures stay put while stepping through versions.
defineProps<{
  added: number
  removed: number
}>()
</script>

<template>
  <span v-if="added || removed" class="inline-flex shrink-0 items-center gap-1.5 text-xs font-medium tabular-nums">
    <span v-if="added" class="text-success">+{{ added }}</span>
    <span v-if="removed" class="text-error">−{{ removed }}</span>
  </span>
</template>
