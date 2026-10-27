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
// Which part of a step's JSON output a mapping reads: the whole output, or a dotted path
// suggested from what its agent returned in recent executions (any other path can be typed).
const props = defineProps<{
  stepKey: string | undefined
  /** Label of the "whole output" choice */
  wholeLabel?: string
  /** Offer the paths to lists too (a score distribution), for formulas that reduce them */
  withLists?: boolean
}>()

const path = defineModel<string | undefined>({ default: undefined })

const WHOLE_OUTPUT = '__whole_output__'

const { pathsOf } = useAgentOutputPaths()
const promptVersions = inject(AGENT_PROMPT_VERSIONS, ref<Record<string, number | undefined>>({}))

// Suggestions come from runs of the source agent with the prompt version the step has here:
// another version may answer in another shape
const known = computed(() => props.stepKey === undefined
  ? pathsOf(undefined)
  : pathsOf(agentIdOfStep(props.stepKey), promptVersions.value[props.stepKey]))

const open = ref(false)
const typed = ref<string[]>([])

const items = computed(() => {
  const lists = new Set(props.withLists ? known.value?.list_paths : [])
  const paths = new Set([...(known.value?.paths ?? []), ...lists, ...typed.value])
  if (path.value)
    paths.add(path.value)
  const unseen = known.value !== null && known.value.paths.length + lists.size === 0
  return [
    { label: props.wholeLabel ?? '(whole output)', value: WHOLE_OUTPUT, list: false },
    ...[...paths].sort().map(p => ({ label: p, value: p, list: lists.has(p) })),
    ...(unseen ? [{ type: 'label' as const, label: 'No run with this prompt version yet: type a path' }] : []),
  ]
})

const selected = computed({
  get: () => path.value || WHOLE_OUTPUT,
  set: (value: string) => {
    path.value = value === WHOLE_OUTPUT ? '' : value
  },
})

function create(value: string) {
  const trimmed = value.trim()
  if (!trimmed)
    return
  typed.value.push(trimmed)
  path.value = trimmed
  open.value = false
}
</script>

<template>
  <USelectMenu
    v-model="selected"
    v-model:open="open"
    :items="items"
    value-key="value"
    create-item="always"
    :search-input="{ placeholder: 'Search or type a path…' }"
    :ui="{ value: 'font-mono text-xs' }"
    size="sm"
    @create="create"
  >
    <template #item-trailing="{ item }">
      <span v-if="(item as { list?: boolean }).list" class="text-xs text-muted" title="A list of values: reduce it with mean(), max(), sum()… or pick one item, like score.0">list</span>
    </template>
    <template #create-item-label="{ item }">
      Use <span class="font-mono text-xs">{{ item }}</span>
    </template>
  </USelectMenu>
</template>
