<script setup lang="ts">
// A provider's logo. Black logos flip to white on dark surfaces; providers without a logo get a muted stand-in.
const props = defineProps<{
  provider: string | null | undefined
}>()

const meta = computed(() => providerMeta(props.provider))
</script>

<template>
  <UIcon
    :name="meta.icon"
    class="size-4 shrink-0"
    :class="[meta.mono && 'dark:invert', meta.generic && 'text-muted']"
    aria-hidden="true"
  />
</template>
