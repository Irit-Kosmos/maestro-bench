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
// The card every graph node shares: a small label above, a header, and the node's details in an inset
// panel. Radii are concentric: the panel's is the card's minus the padding between them.
defineProps<{
  /** Small label above the card, e.g. "Step 2" */
  kicker: string
  icon: string
  title: string
  subtitle?: string
  selected?: boolean
  /** The node is switched off: it stays on the graph, but recedes */
  muted?: boolean
  /** Tints the icon: the node is a computation rather than a model call */
  accent?: boolean
}>()

defineSlots<{
  /** Right of the title */
  aside?: () => any
  /** The inset panel */
  default?: () => any
  /** Below the card, outside it */
  footer?: () => any
}>()
</script>

<template>
  <div class="group/card relative transition-opacity duration-150 ease-out" :class="{ 'opacity-60': muted }">
    <div
      class="absolute bottom-full left-1.5 mb-[7px] text-[10px] leading-none font-medium tracking-[0.06em] whitespace-nowrap uppercase transition-colors duration-150 ease-out"
      :class="selected ? 'text-highlighted' : 'text-muted'"
    >
      {{ kicker }}
    </div>

    <div
      class="rounded-[14px] border bg-default p-1 transition-[border-color,box-shadow] duration-150 ease-out"
      :class="selected
        ? 'border-inverted shadow-[0_0_0_3px_color-mix(in_oklab,var(--ui-text-highlighted)_14%,transparent),0_6px_14px_-8px_rgb(0_0_0/0.1)]'
        : 'border-default shadow-[0_1px_2px_rgb(0_0_0/0.04),0_6px_14px_-8px_rgb(0_0_0/0.1)] group-hover/card:border-accented'"
    >
      <header class="flex items-center gap-2.5 pt-1.5 pr-2 pb-2 pl-1.5">
        <span
          class="grid size-7 shrink-0 place-items-center rounded-lg border"
          :class="accent ? 'border-accented bg-elevated text-highlighted' : 'border-default bg-muted text-muted'"
        >
          <UIcon :name="icon" class="size-4" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium text-highlighted" :title="title">
            {{ title }}
          </div>
          <div v-if="subtitle" class="mt-px truncate text-xs text-muted" :title="subtitle">
            {{ subtitle }}
          </div>
        </div>
        <slot name="aside" />
      </header>

      <!-- 14px card - 4px padding - 1px border: the panel's corners follow the card's -->
      <div v-if="$slots.default" class="flex flex-col gap-1.5 rounded-[9px] border border-muted bg-muted px-2.5 py-2">
        <slot />
      </div>
    </div>

    <slot name="footer" />
  </div>
</template>
