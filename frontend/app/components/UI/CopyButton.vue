<script setup lang="ts">
// Copies text, and says so: the copy icon swaps for a check with a scale + blur crossfade,
// so the two read as one icon changing state rather than two icons overlapping.
const props = defineProps<{
  text: string
  /** What is being copied, for the accessible name */
  label: string
}>()

const copied = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
  }
  catch {
    return
  }
  copied.value = true
  clearTimeout(timer)
  timer = setTimeout(() => copied.value = false, 1500)
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <UTooltip :text="copied ? 'Copied' : 'Copy'" :delay-duration="400">
    <UButton
      color="neutral"
      variant="ghost"
      size="xs"
      square
      :aria-label="copied ? 'Copied' : `Copy ${label}`"
      :ui="{ base: 'not-disabled:not-aria-disabled:active:scale-95' }"
      @click="copy"
    >
      <span class="relative block size-4" aria-hidden="true">
        <UIcon name="i-ph-copy-bold" class="copy-icon absolute inset-0 size-4" :data-hidden="copied || undefined" />
        <UIcon name="i-ph-check-bold" class="copy-icon absolute inset-0 size-4 text-success" :data-hidden="!copied || undefined" />
      </span>
    </UButton>
  </UTooltip>
</template>

<style scoped>
.copy-icon {
  transition: opacity 200ms var(--ease-out), scale 200ms var(--ease-out), filter 200ms var(--ease-out);
}

.copy-icon[data-hidden] {
  opacity: 0;
  scale: 0.25;
  filter: blur(4px);
}

/* Reduced motion keeps the swap, drops the movement */
@media (prefers-reduced-motion: reduce) {
  .copy-icon {
    transition: opacity 150ms ease;
  }

  .copy-icon[data-hidden] {
    scale: 1;
    filter: none;
  }
}
</style>
