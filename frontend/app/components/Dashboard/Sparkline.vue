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
// One bar per slice of the period, tallest where the figure peaks. The card carries the figure
// itself: the bars are there to be hovered, each naming its slice at once (no delay, the first
// tooltip of a sweep included). The color is the text's. Assistive tech gets every slice in one label.
const props = defineProps<{
  values: readonly number[]
  /** What each bar stands for, in the same order as `values` */
  labels?: readonly string[]
}>()

const summary = computed(() => props.labels?.filter(Boolean).join(', '))

const bars = computed(() => {
  const peak = Math.max(...props.values, 0)
  return props.values.map((value, i) => ({
    // Slices with nothing keep a hairline, so the time axis stays visible
    height: value > 0 ? `${Math.max(8, (value / peak) * 100)}%` : '1px',
    empty: value <= 0,
    label: props.labels?.[i],
  }))
})
</script>

<template>
  <div v-if="values.length" class="flex h-10 w-24 shrink-0 items-stretch gap-0.5" :role="summary ? 'img' : undefined" :aria-label="summary || undefined" :aria-hidden="summary ? undefined : true">
    <UTooltip
      v-for="(bar, i) in bars"
      :key="i"
      :text="bar.label"
      :disabled="!bar.label"
      :delay-duration="0"
      :content="{ side: 'top', sideOffset: 4 }"
    >
      <div class="group flex min-w-0 flex-1 items-end rounded-xs hover:bg-elevated">
        <div
          class="w-full rounded-[1px] bg-current"
          :class="bar.empty ? 'opacity-25' : 'group-hover:opacity-70'"
          :style="{ height: bar.height }"
        />
      </div>
    </UTooltip>
  </div>
</template>
