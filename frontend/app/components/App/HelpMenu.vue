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
    ? [{
        label: 'Source code',
        icon: 'i-ph-code',
        to: sourceUrl,
        target: '_blank',
        slot: 'external' as const,
        // Items align to the top (items-start), so a trailing icon shorter than the label line sits high
        ui: { itemTrailing: 'self-center' },
      }]
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
