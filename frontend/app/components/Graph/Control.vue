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
// A button of the canvas's floating toolbar. Tooltips come from the toolbar's UITooltipGroup (data-tooltip)
defineProps<{
  label: string
  icon?: string
  kbd?: string
  disabled?: boolean
  pressed?: boolean
}>()
</script>

<template>
  <button
    type="button"
    class="inline-flex h-7 min-w-7 items-center justify-center rounded-md text-muted transition-[background-color,color,scale] duration-120 ease-out enabled:hover:bg-elevated enabled:hover:text-highlighted enabled:active:scale-95 aria-pressed:text-highlighted disabled:cursor-default disabled:opacity-40 focus-visible:outline-2 focus-visible:-outline-offset-1 focus-visible:outline-inverted"
    :aria-label="label"
    :aria-pressed="pressed"
    :data-tooltip="label"
    :data-tooltip-kbds="kbd"
    :disabled="disabled"
  >
    <slot>
      <UIcon v-if="icon" :name="icon" class="size-3.5" aria-hidden="true" />
    </slot>
  </button>
</template>
