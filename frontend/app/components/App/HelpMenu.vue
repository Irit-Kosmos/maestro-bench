<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{ collapsed?: boolean }>()

const shortcutsOpen = useShortcutsOverlay()
// Empty when the instance hides it (NUXT_PUBLIC_SOURCE_URL='')
const sourceUrl = useRuntimeConfig().public.SOURCE_URL as string

const items = computed<DropdownMenuItem[]>(() => [
  {
    label: 'Keyboard shortcuts',
    icon: 'i-ph-keyboard',
    kbds: ['?'],
    onSelect: () => {
      shortcutsOpen.value = true
    },
  },
  ...(sourceUrl
    ? [{ label: 'Source code', icon: 'i-ph-code', to: sourceUrl, target: '_blank', slot: 'external' as const }]
    : []),
])
</script>

<template>
  <UTooltip text="Help" :content="{ side: collapsed ? 'right' : 'top' }">
    <UDropdownMenu
      :items="items"
      :content="{ side: collapsed ? 'right' : 'top', align: 'end' }"
      :ui="{ content: 'w-52' }"
      :external-icon="false"
    >
      <UButton
        icon="i-ph-question"
        color="neutral"
        variant="ghost"
        size="sm"
        aria-label="Help"
      />

      <!-- Nuxt UI's own external icon sits superscript on the label; here it lines up on the right, like the kbds -->
      <template #external-trailing>
        <UIcon name="i-ph-arrow-up-right" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
      </template>
    </UDropdownMenu>
  </UTooltip>
</template>
