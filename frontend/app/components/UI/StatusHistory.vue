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
// The earlier executions of an experiment (or of a batch's experiments), as a row of small status icons next to its status.
// Nothing while there is no earlier execution.
const props = withDefaults(defineProps<{
  /** Status of the executions before the latest one, from the newest to the oldest */
  earlier?: readonly string[] | null
  /** Icons shown before the rest is counted */
  max?: number
}>(), {
  max: 4,
})

const runs = computed(() => props.earlier ?? [])

const shown = computed(() => runs.value.slice(0, props.max))

const hidden = computed(() => runs.value.length - shown.value.length)

const summary = computed(() => {
  const counts = new Map<string, number>()
  for (const run of runs.value)
    counts.set(run, (counts.get(run) ?? 0) + 1)
  return `Earlier runs: ${[...counts].map(([run, count]) => `${count} ${run}`).join(', ')}`
})
</script>

<template>
  <UTooltip v-if="runs.length" :text="summary">
    <!-- Focusable so the summary opens from the keyboard; raised above a row's stretched link so the pointer reaches it -->
    <span
      tabindex="0"
      class="relative z-1 inline-flex items-center rounded-sm text-xs text-muted tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-inverted"
    >
      <!-- Shapes, not just colors, tell the runs apart; the summary says it in words. The icons' own titles stay out of the way -->
      <span class="pointer-events-none flex items-center gap-0.5" aria-hidden="true">
        <UIStatusIcon v-for="(run, index) in shown" :key="index" :status="run" size="size-3" />
      </span>
      <span v-if="hidden" class="ms-1" aria-hidden="true">+{{ hidden }}</span>
      <span class="sr-only">{{ summary }}</span>
    </span>
  </UTooltip>
</template>
