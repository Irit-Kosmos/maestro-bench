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
import type { DashboardActiveExperiment } from '~/types'

// Shown only while something runs or waits to: the rest of the time it takes no room.
// One experiment goes straight to it, with its progress; several go to the list.
const props = defineProps<{
  active: readonly DashboardActiveExperiment[]
}>()

const { runOf } = useLiveRuns()

const running = computed(() => props.active.filter(exp => exp.status === 'running'))
const queued = computed(() => props.active.length - running.value.length)
const first = computed(() => props.active[0])
const single = computed(() => props.active.length === 1)

const summary = computed(() => {
  const parts = []
  if (running.value.length)
    parts.push(`${running.value.length} running`)
  if (queued.value)
    parts.push(`${queued.value} queued`)
  return parts.join(' · ')
})
</script>

<template>
  <NuxtLink
    v-if="first"
    :to="single ? `/experiments/${first.id}` : '/experiments'"
    class="flex items-center gap-2.5 h-10 px-4 rounded-lg border border-info/30 bg-info/10 text-sm text-toned outline-none hover:bg-info/15 focus-visible:ring-2 focus-visible:ring-inverted"
  >
    <span
      class="size-1.5 shrink-0 rounded-full bg-info"
      :class="{ 'motion-safe:animate-pulse': running.length }"
      aria-hidden="true"
    />
    <span class="shrink-0 font-medium text-highlighted">{{ summary }}</span>
    <span class="min-w-0 truncate text-muted">
      {{ first.name }}<template v-if="!single"> and {{ active.length - 1 }} more</template>
    </span>
    <UIRunProgress v-if="single" :run="runOf(first.id)" class="ms-auto shrink-0" />
    <UIcon
      name="i-ph-arrow-right-bold"
      class="size-3.5 shrink-0 text-highlighted"
      :class="{ 'ms-auto': !single }"
      aria-hidden="true"
    />
  </NuxtLink>
</template>
