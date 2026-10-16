<script setup lang="ts">
// Copies text, and says so: the copy icon swaps for a check (or a cross when the browser refuses) with a scale + blur
// crossfade, so they read as one icon changing state rather than icons overlapping.
const props = withDefaults(defineProps<{
  text: string
  /** What is being copied, for the accessible name */
  label: string
  /** Ghost xs by default, as a side action; outline md where copying is the point and it sits next to a field */
  size?: 'xs' | 'md'
  variant?: 'ghost' | 'outline'
}>(), { size: 'xs', variant: 'ghost' })

const state = ref<'idle' | 'copied' | 'failed'>('idle')
const { fail } = useStandardToast()
let timer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
  }
  catch {
    show('failed')
    fail('Couldn’t copy', 'Select the text and copy it manually.')
    return
  }
  show('copied')
}

function show(next: 'copied' | 'failed') {
  state.value = next
  clearTimeout(timer)
  timer = setTimeout(() => state.value = 'idle', 1500)
}

const TEXTS = { idle: 'Copy', copied: 'Copied', failed: 'Couldn’t copy' }

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <UTooltip :text="TEXTS[state]" :delay-duration="400">
    <UButton
      color="neutral"
      :variant="variant"
      :size="size"
      square
      :aria-label="state === 'idle' ? `Copy ${label}` : TEXTS[state]"
      @click="copy"
    >
      <span class="relative block size-4" aria-hidden="true">
        <UIcon name="i-ph-copy-bold" class="copy-icon absolute inset-0 size-4" :data-hidden="state !== 'idle' || undefined" />
        <UIcon name="i-ph-check-bold" class="copy-icon absolute inset-0 size-4 text-success" :data-hidden="state !== 'copied' || undefined" />
        <UIcon name="i-ph-x-bold" class="copy-icon absolute inset-0 size-4 text-error" :data-hidden="state !== 'failed' || undefined" />
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
