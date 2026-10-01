<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{ collapsed?: boolean }>()

const { colorMode } = useTheme()

type Preference = 'light' | 'dark' | 'system'

const options: { value: Preference, label: string, icon: string }[] = [
  { value: 'light', label: 'Light', icon: 'i-lucide-sun' },
  { value: 'dark', label: 'Dark', icon: 'i-lucide-moon' },
  { value: 'system', label: 'System', icon: 'i-lucide-monitor' },
]

const items = computed<DropdownMenuItem[]>(() => options.map(option => ({
  label: option.label,
  icon: option.icon,
  type: 'checkbox',
  checked: colorMode.preference === option.value,
  onSelect: () => {
    colorMode.preference = option.value
  },
})))
</script>

<template>
  <UTooltip text="Theme" :kbds="['T']" :content="{ side: collapsed ? 'right' : 'top' }">
    <UDropdownMenu
      :items="items"
      :content="{ side: collapsed ? 'right' : 'top', align: 'end' }"
      :ui="{ content: 'w-36' }"
    >
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        aria-label="Change theme"
      >
        <!-- Both icons stay mounted and crossfade: the blur hides the overlap between the two shapes -->
        <span class="relative block size-4" aria-hidden="true">
          <UIcon
            name="i-lucide-sun"
            data-theme-icon
            class="theme-icon absolute inset-0 size-4 dark:scale-90 dark:opacity-0 dark:blur-[2px]"
          />
          <UIcon
            name="i-lucide-moon"
            data-theme-icon
            class="theme-icon absolute inset-0 size-4 scale-90 opacity-0 blur-[2px] dark:scale-100 dark:opacity-100 dark:blur-none"
          />
        </span>
      </UButton>
    </UDropdownMenu>
  </UTooltip>
</template>

<style scoped>
.theme-icon {
  transition: opacity 200ms var(--ease-out), scale 200ms var(--ease-out), filter 200ms var(--ease-out);
}

@media (prefers-reduced-motion: reduce) {
  .theme-icon {
    transition: opacity 150ms ease;
    scale: 1 !important;
    filter: none !important;
  }
}
</style>
