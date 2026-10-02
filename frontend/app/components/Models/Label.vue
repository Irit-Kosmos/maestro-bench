<script setup lang="ts">
// A model as it reads in lists and summaries: its provider's logo, then its name
defineProps<{
  name: string
  provider?: string | null
  /** Provider name after the model name, for places where the logo alone is not enough */
  showProvider?: boolean
}>()
</script>

<template>
  <span class="inline-flex min-w-0 items-center gap-1.5 align-middle">
    <UIProviderIcon v-if="provider" :provider="provider" class="size-3.5" />
    <span class="truncate">{{ name }}</span>
    <span v-if="showProvider && provider" class="shrink-0 text-muted">{{ providerLabel(provider) }}</span>
  </span>
</template>
