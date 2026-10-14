<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{ collapsed?: boolean }>()

// Linear's workspace menu: who you are, this workspace's settings, the way out to the others, sign out
const { user, logout } = useAuth()
const { workspace, can } = useCurrentWorkspace()

const items = computed<DropdownMenuItem[][]>(() => [
  [
    {
      type: 'label',
      label: user.value?.display_name,
      description: user.value?.email ?? undefined,
      avatar: { src: user.value?.avatar_url ?? undefined, alt: user.value?.display_name },
    },
  ],
  [
    { label: 'Settings', icon: 'i-ph-gear', kbds: ['G', 'S'], to: '/settings' },
    ...(can('owner') ? [{ label: 'Invite and manage members', icon: 'i-ph-users', to: '/settings#members' }] : []),
  ],
  [
    { label: 'Switch workspace', icon: 'i-ph-arrows-left-right', kbds: ['O', 'W'], to: '/w' },
    { label: 'Log out', icon: 'i-ph-sign-out', onSelect: logout },
  ],
])
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ side: collapsed ? 'right' : 'bottom', align: 'start' }"
    :ui="{ content: 'w-64' }"
  >
    <UButton
      color="neutral"
      variant="ghost"
      size="sm"
      class="h-8 select-none active:scale-100!"
      :class="collapsed ? 'mx-auto justify-center px-1.5' : 'min-w-0 flex-1 justify-start gap-2 px-1'"
      :aria-label="`${workspace?.name ?? 'MAESTRO-bench'}, workspace menu`"
    >
      <AppLogo class="size-5 shrink-0 text-highlighted" />
      <span v-if="!collapsed" class="min-w-0 flex-1 truncate text-start text-sm font-semibold text-highlighted">
        {{ workspace?.name ?? 'MAESTRO-bench' }}
      </span>
      <UIcon v-if="!collapsed" name="i-ph-caret-down" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
    </UButton>
  </UDropdownMenu>
</template>
