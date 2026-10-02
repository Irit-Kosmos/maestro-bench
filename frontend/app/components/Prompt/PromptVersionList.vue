<script setup lang="ts">
import type { PromptVersion } from '~/types'

// The versions of a prompt, one dense row each; the selected one is read or edited beside it.
defineProps<{
  versions: readonly PromptVersion[]
  selectedId: number | null
  /** A new version is being written: show it as the selected row */
  drafting: boolean
}>()

const emit = defineEmits<{
  select: [id: number]
  create: []
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()

const rowClass = 'flex h-9 w-full items-center gap-2 px-4 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary'
</script>

<template>
  <nav aria-label="Versions" class="flex min-h-0 flex-col">
    <header class="flex h-11 shrink-0 items-center justify-between gap-2 border-b border-default ps-4 pe-2">
      <h2 class="text-sm font-medium text-highlighted">
        Versions
        <span class="ms-1 text-xs font-normal text-muted tabular-nums">{{ versions.length }}</span>
      </h2>
      <UTooltip :delay-duration="400">
        <UButton
          icon="i-lucide-plus"
          color="neutral"
          variant="ghost"
          size="sm"
          aria-label="New version"
          @click="emit('create')"
        />
        <template #content>
          <span class="flex items-center gap-1.5">New version <UKbd value="n" size="sm" /></span>
        </template>
      </UTooltip>
    </header>

    <ul class="min-h-0 flex-1 divide-y divide-default overflow-y-auto">
      <li v-if="drafting">
        <div :class="rowClass" class="bg-elevated text-highlighted" aria-current="true">
          <UIcon name="i-lucide-plus" class="size-4 shrink-0 text-muted" aria-hidden="true" />
          <span class="truncate font-medium">New version</span>
        </div>
      </li>

      <li v-for="version in versions" :key="version.id">
        <button
          type="button"
          :class="rowClass"
          class="hover:bg-elevated/50"
          :aria-current="!drafting && version.id === selectedId ? 'true' : undefined"
          :data-selected="!drafting && version.id === selectedId ? '' : undefined"
          @click="emit('select', version.id)"
        >
          <span
            class="min-w-0 truncate font-medium"
            :class="version.is_active ? 'text-highlighted' : 'text-muted'"
          >
            {{ version.version }}
          </span>
          <span v-if="version.is_default" class="shrink-0 text-xs text-success">Default</span>
          <span v-else-if="!version.is_active" class="shrink-0 text-xs text-dimmed">Inactive</span>
          <span
            class="ms-auto shrink-0 text-xs text-dimmed tabular-nums"
            :title="formatDate(version.created_at)"
          >
            {{ formatRelativeDate(version.created_at) }}
          </span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
/* Selected row: raised surface, plus an edge so it reads without colour */
[data-selected] {
  background-color: var(--ui-bg-elevated);
  box-shadow: inset 2px 0 0 var(--ui-primary);
}
</style>
