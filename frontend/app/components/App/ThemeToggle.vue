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

const { colorMode } = useTheme()

type Preference = 'light' | 'dark' | 'system'

const options: { value: Preference, label: string, icon: string }[] = [
  { value: 'light', label: 'Light', icon: 'i-ph-sun-bold' },
  { value: 'dark', label: 'Dark', icon: 'i-ph-moon-bold' },
  { value: 'system', label: 'System', icon: 'i-ph-monitor-bold' },
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

// Reduced motion keeps the crossfade, drops the scale and the blur
const iconClass = 'transition-[opacity,scale,filter] duration-200 ease-out motion-reduce:scale-100! motion-reduce:filter-none! motion-reduce:transition-opacity motion-reduce:duration-150 motion-reduce:ease-[ease]'
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
            name="i-ph-sun-bold"
            data-theme-icon
            :class="iconClass" class="absolute inset-0 size-4 dark:scale-90 dark:opacity-0 dark:blur-[2px]"
          />
          <UIcon
            name="i-ph-moon-bold"
            data-theme-icon
            :class="iconClass" class="absolute inset-0 size-4 scale-90 opacity-0 blur-[2px] dark:scale-100 dark:opacity-100 dark:blur-none"
          />
        </span>
      </UButton>
    </UDropdownMenu>
  </UTooltip>
</template>
