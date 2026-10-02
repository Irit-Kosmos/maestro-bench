<script setup lang="ts">
// A provider's logo. Black logos flip to white on dark surfaces; providers without a logo get a muted stand-in.
const props = defineProps<{
  provider: string | null | undefined
  // Sits on an always-light surface, so black logos stay black in dark mode
  onLight?: boolean
}>()

const meta = computed(() => providerMeta(props.provider))
</script>

<template>
  <UIcon
    :name="meta.icon"
    class="size-4 shrink-0"
    :class="[meta.mono && !onLight && 'dark:invert', meta.generic && !onLight && 'text-muted']"
    aria-hidden="true"
  />
</template>
