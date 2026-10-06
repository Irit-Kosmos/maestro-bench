<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{ collapsed?: boolean }>()

const { user, logout } = useAuth()
const shortcutsOpen = useShortcutsOverlay()

const items = computed<DropdownMenuItem[][]>(() => [
  [
    {
      type: 'label',
      label: user.value?.display_name,
      description: user.value?.email ?? undefined,
    },
  ],
  [
    {
      label: 'Keyboard shortcuts',
      icon: 'i-ph-keyboard',
      kbds: ['?'],
      onSelect: () => {
        shortcutsOpen.value = true
      },
    },
  ],
  [
    { label: 'Sign out', icon: 'i-ph-sign-out', onSelect: logout },
  ],
])
</script>

<template>
  <UDropdownMenu
    v-if="user"
    :items="items"
    :content="{ side: collapsed ? 'right' : 'top', align: 'start' }"
    :ui="{ content: 'w-56' }"
  >
    <UButton
      color="neutral"
      variant="ghost"
      size="sm"
      :aria-label="collapsed ? `Account: ${user.display_name}` : undefined"
      :class="collapsed ? 'justify-center' : 'min-w-0 flex-1 justify-start'"
      class="active:scale-100!"
    >
      <UAvatar :src="user.avatar_url ?? undefined" :alt="user.display_name" size="2xs" />
      <span v-if="!collapsed" class="flex-1 min-w-0 truncate text-start">{{ user.display_name }}</span>
    </UButton>
  </UDropdownMenu>
</template>
