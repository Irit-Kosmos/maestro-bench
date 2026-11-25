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
import type { ExecutionFailures, FailureGroup } from '~/types'

// The failed rows of an execution, grouped by the step and error that stopped them:
// most runs fail many rows for one reason (rate limit, timeout), said once with its rows.
const props = defineProps<{
  executionId: number
}>()

const emit = defineEmits<{
  /** The failures are on screen (or known to be missing): the block has its final height */
  loaded: []
}>()
// Rows listed per group before "+N more"
const ROWS_SHOWN = 20
// Messages longer than this are clamped to two lines until opened
const LONG_MESSAGE = 140

const { fetchExecutionFailures } = useExperimentExecutions()

const failures = ref<ExecutionFailures | null>(null)
const loading = ref(true)
const loadFailed = ref(false)

async function load() {
  loading.value = true
  loadFailed.value = false
  try {
    failures.value = await fetchExecutionFailures(props.executionId)
  }
  catch {
    loadFailed.value = true
  }
  finally {
    loading.value = false
    emit('loaded')
  }
}
onMounted(load)

// Per group (by position): all its rows listed, its message in full
const allRows = ref(new Set<number>())
const fullMessage = ref(new Set<number>())
function toggle(set: Set<number>, i: number) {
  if (set.has(i))
    set.delete(i)
  else
    set.add(i)
}

function shownRows(group: FailureGroup, i: number) {
  return allRows.value.has(i) ? group.rows : group.rows.slice(0, ROWS_SHOWN)
}

// One panel for the execution; it steps through the rows of the group it was opened on
const panelOpen = ref(false)
const panelGroup = ref<FailureGroup | null>(null)
const panelIndex = ref(0)
function openRow(group: FailureGroup, index: number) {
  panelGroup.value = group
  panelIndex.value = index
  panelOpen.value = true
}
</script>

<template>
  <div>
    <div v-if="loading" class="flex flex-col gap-1.5 py-1" aria-busy="true">
      <span class="sr-only">Loading failures…</span>
      <USkeleton class="h-3 w-2/5" />
      <USkeleton class="h-3 w-4/5" />
    </div>

    <p v-else-if="loadFailed" class="flex items-center gap-2 text-xs text-muted">
      Couldn’t load what failed.
      <UButton label="Retry" variant="link" color="neutral" size="xs" class="p-0" @click="load" />
    </p>

    <p v-else-if="!failures?.groups.length" class="text-xs text-muted text-pretty">
      No details: the run stopped before writing its results.
    </p>

    <ul v-else class="divide-y divide-default rounded-md bg-elevated/50 px-2.5">
      <li v-for="(group, i) in failures.groups" :key="i" class="flex flex-col gap-1.5 py-2.5">
        <div class="flex min-w-0 items-center gap-2 text-xs">
          <span v-if="group.agent_name" class="flex min-w-0 items-center gap-1 text-toned" :title="`Failed at ${group.agent_name}`">
            <UIcon name="i-ph-ghost-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
            <span class="sr-only">Failed at </span>
            <span class="truncate font-medium">{{ group.agent_name }}</span>
          </span>
          <span v-else class="text-muted">Before any agent</span>
          <span class="ms-auto shrink-0 text-muted tabular-nums">{{ formatRows(group.rows.length) }}</span>
        </div>

        <div class="text-xs text-error">
          <p
            :id="`failure-${executionId}-${i}`"
            class="whitespace-pre-wrap break-words"
            :class="{ 'line-clamp-2': !fullMessage.has(i) }"
          >
            {{ group.message }}
          </p>
          <button
            v-if="group.message.length > LONG_MESSAGE || group.message.includes('\n')"
            type="button"
            class="mt-0.5 rounded-sm text-muted outline-none hover:text-highlighted focus-visible:outline-2 focus-visible:outline-inverted"
            :aria-expanded="fullMessage.has(i)"
            :aria-controls="`failure-${executionId}-${i}`"
            @click="toggle(fullMessage, i)"
          >
            {{ fullMessage.has(i) ? 'Show less' : 'Show more' }}
          </button>
        </div>

        <!-- Each row opens in full: what went in, what the agents were sent, what stopped them -->
        <ul class="flex flex-wrap gap-1" :aria-label="`Rows that failed at ${group.agent_name ?? 'the start'}`">
          <li v-for="(rowIndex, r) in shownRows(group, i)" :key="rowIndex">
            <button
              type="button"
              class="h-6 min-w-6 rounded-sm bg-default px-1.5 font-mono text-[0.6875rem] text-toned tabular-nums ring ring-default outline-none transition-[scale,background-color,color] duration-150 ease-(--ease-out) hover:bg-accented/50 hover:text-highlighted focus-visible:outline-2 focus-visible:outline-inverted active:scale-[0.96] motion-reduce:transition-none"
              :aria-label="`Open row ${rowIndex}`"
              @click="openRow(group, r)"
            >
              {{ rowIndex }}
            </button>
          </li>
          <li v-if="group.rows.length > ROWS_SHOWN">
            <button
              type="button"
              class="h-6 rounded-sm px-1.5 text-[0.6875rem] text-muted tabular-nums outline-none hover:text-highlighted focus-visible:outline-2 focus-visible:outline-inverted"
              @click="toggle(allRows, i)"
            >
              {{ allRows.has(i) ? 'Show fewer' : `+${group.rows.length - ROWS_SHOWN} more` }}
            </button>
          </li>
        </ul>
      </li>
    </ul>

    <ExperimentsFailedRowPanel
      v-model:open="panelOpen"
      v-model:index="panelIndex"
      :execution-id="executionId"
      :group="panelGroup"
    />
  </div>
</template>
