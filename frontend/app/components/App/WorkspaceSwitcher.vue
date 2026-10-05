<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const { slug } = useWorkspace()
const { workspaces, open } = useWorkspaces()
const { canCreateWorkspace } = useAuth()

const current = computed(() => workspaces.value?.find(w => w.slug === slug.value))

const items = computed<DropdownMenuItem[][]>(() => [
  (workspaces.value ?? []).map(workspace => ({
    label: workspace.name,
    type: 'checkbox' as const,
    checked: workspace.slug === slug.value,
    onSelect: () => workspace.slug === slug.value ? undefined : open(workspace.slug),
  })),
  [
    { label: 'All workspaces', icon: 'i-ph-squares-four', to: '/w' },
    ...(canCreateWorkspace.value ? [{ label: 'New workspace', icon: 'i-ph-plus', to: '/w?new=1' }] : []),
  ],
])
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ side: 'bottom', align: 'start' }"
    :ui="{ content: 'w-60' }"
  >
    <UButton
      color="neutral"
      variant="ghost"
      size="sm"
      class="min-w-0 flex-1 justify-start gap-2 px-1 h-8 select-none active:scale-100!"
      :aria-label="`Workspace: ${current?.name ?? ''}`"
    >
      <img
        src="/MAESTRO-bench.png"
        alt=""
        class="shrink-0 h-6 w-auto"
      >
      <span class="min-w-0 flex-1 truncate text-start text-sm font-semibold text-highlighted">
        {{ current?.name ?? 'MAESTRO-bench' }}
      </span>
      <UIcon name="i-ph-caret-up-down" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
    </UButton>
  </UDropdownMenu>
</template>
