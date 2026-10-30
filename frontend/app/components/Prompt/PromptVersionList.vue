<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { PromptVersion } from '~/types'
import type { LineCounts } from '~/utils/textDiff'

// The versions of a prompt, one dense row each; the selected one is read or edited beside it.
const props = defineProps<{
  versions: readonly PromptVersion[]
  selectedId: number | null
  /** A new version is being written: show it as the selected row */
  drafting: boolean
  /** Lines changed against the version before, once computed */
  stats: ReadonlyMap<number, LineCounts>
}>()

const emit = defineEmits<{
  select: [id: number]
  create: []
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

// Nothing to show for a version that matches the one before it, or the oldest
function changed(id: number) {
  const counts = props.stats.get(id)
  return counts && (counts.added || counts.removed) ? counts : null
}

const rowClass = 'flex h-9 w-full items-center gap-2 px-4 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted'
</script>

<template>
  <nav aria-label="Versions" class="flex min-h-0 flex-col">
    <header class="flex h-11 shrink-0 items-center justify-between gap-2 border-b border-default ps-4 pe-2">
      <h2 class="text-sm font-medium text-highlighted">
        Versions
        <span class="ms-1 text-xs font-normal text-muted tabular-nums">{{ versions.length }}</span>
      </h2>
      <UTooltip v-if="canEdit" :delay-duration="400">
        <UButton
          icon="i-ph-plus-bold"
          color="neutral"
          variant="ghost"
          size="sm"
          aria-label="New version"
          @click="emit('create')"
        />
        <template #content>
          <span class="flex items-center gap-1.5">New version <BaseKbd value="n" /></span>
        </template>
      </UTooltip>
    </header>

    <ul class="min-h-0 flex-1 divide-y divide-default overflow-y-auto">
      <li v-if="drafting">
        <div :class="rowClass" class="bg-elevated text-highlighted" aria-current="true">
          <UIcon name="i-ph-plus-bold" class="size-4 shrink-0 text-muted" aria-hidden="true" />
          <span class="truncate font-medium">New version</span>
        </div>
      </li>

      <li v-for="version in versions" :key="version.id">
        <!-- Selected row: raised surface, plus an edge so it reads without colour -->
        <button
          type="button"
          class="flex w-full flex-col gap-0.5 px-4 py-2 text-left text-sm outline-none not-data-selected:hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted data-selected:bg-elevated data-selected:shadow-[inset_2px_0_0_var(--ui-primary)]"
          :aria-current="!drafting && version.id === selectedId ? 'true' : undefined"
          :data-selected="!drafting && version.id === selectedId ? '' : undefined"
          @click="emit('select', version.id)"
        >
          <span class="flex w-full items-center gap-2">
            <span
              class="min-w-0 truncate font-medium"
              :class="version.is_active ? 'text-highlighted' : 'text-muted'"
            >
              {{ version.version }}
            </span>
            <span v-if="version.is_default" class="shrink-0 text-xs text-primary-700 dark:text-primary">Default</span>
            <span v-else-if="!version.is_active" class="shrink-0 text-xs text-muted">Inactive</span>
            <BaseDiffStat
              v-if="changed(version.id)"
              :added="changed(version.id)!.added"
              :removed="changed(version.id)!.removed"
              class="ms-auto"
            />
          </span>
          <!-- Who wrote it and when, as a commit reads -->
          <span class="flex w-full min-w-0 items-center gap-1.5 text-xs text-muted">
            <template v-if="version.author">
              <UIPerson :person="version.author" label="Created by" class="text-toned" />
              <span aria-hidden="true">·</span>
            </template>
            <span class="shrink-0" :title="formatDate(version.created_at)">{{ formatRelativeDate(version.created_at) }}</span>
          </span>
        </button>
      </li>
    </ul>
  </nav>
</template>
