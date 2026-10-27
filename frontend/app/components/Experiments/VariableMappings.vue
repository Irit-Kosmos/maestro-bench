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
import type { StepRef } from '~/composables/useAgentPipeline'
import type { AgentInputMapping } from '~/types'

// Where each variable gets its value for every row: a dataset column, an earlier agent's output
// (whole, or one field of its JSON), or a fixed value. Shared by prompt variables and formula variables.
const props = withDefaults(defineProps<{
  variables: readonly string[]
  mappings: readonly AgentInputMapping[] | undefined
  datasetHeaders: readonly string[]
  /** Steps whose output may be read, nearest last */
  upstreamSteps: readonly StepRef[]
  title: string
  description: string
  staticLabel?: string
  staticPlaceholder?: string
  isComplete?: (mapping: AgentInputMapping | undefined) => boolean
  /** Offer agent output fields that hold lists */
  withLists?: boolean
  /** Tighter type and rows, for a side panel */
  compact?: boolean
}>(), {
  staticLabel: 'Fixed text',
  staticPlaceholder: 'Text sent on every row',
  isComplete: isMappingComplete,
})

const emit = defineEmits<{
  setMapping: [mapping: AgentInputMapping]
  /** The variable under the pointer or focus, or null once it leaves */
  highlight: [variable: string | null]
}>()

const ids = useId()

const rows = computed(() => props.variables.map(variable => ({
  variable,
  mapping: props.mappings?.find(m => m.variable === variable),
})))

const mappedCount = computed(() => rows.value.filter(row => props.isComplete(row.mapping)).length)

const columnItems = computed(() => props.datasetHeaders.map(h => ({ label: h, value: h })))
const upstreamItems = computed(() => props.upstreamSteps.map(step => ({ label: step.label, value: step.key })))

// "Previous agent" only makes sense once something runs before this agent (unless it is already chosen)
function sourceItems(current: AgentInputMapping | undefined) {
  return [
    { label: 'Dataset column', value: 'dataset' },
    ...(props.upstreamSteps.length > 0 || current?.source === 'agent' ? [{ label: 'Previous agent', value: 'agent' }] : []),
    { label: props.staticLabel, value: 'static' },
  ]
}

const simplify = (name: string) => name.toLowerCase().replace(/[^a-z0-9]/g, '')

// The step a variable most likely reads, shown in the select so a wrong guess is easy to see:
// one named like it ("content" or "c" for Content), else the nearest one no other variable reads yet
function defaultSourceStep(variable: string): string | undefined {
  const candidates = props.upstreamSteps
  const name = simplify(variable)
  const named = candidates.find(step => simplify(step.label) === name)
    ?? (name ? candidates.find(step => simplify(step.label).startsWith(name)) : undefined)
  if (named)
    return named.key
  const taken = new Set((props.mappings ?? [])
    .filter(m => m.source === 'agent' && m.variable !== variable)
    .map(mappingSource))
  return [...candidates].reverse().find(step => !taken.has(step.key))?.key ?? candidates.at(-1)?.key
}

function chooseSource(variable: string, source: AgentInputMapping['source']) {
  const existing = props.mappings?.find(m => m.variable === variable)
  if (existing?.source === source)
    return
  const mapping: AgentInputMapping = { variable, source }
  // A dataset column is left for the user to pick: guessing the first one would be silently wrong
  if (source === 'agent') {
    mapping.sourceStep = defaultSourceStep(variable)
    mapping.sourceOutput = 'output'
  }
  else if (source === 'static') {
    mapping.staticValue = ''
  }
  emit('setMapping', mapping)
}

function patchMapping(row: (typeof rows.value)[number], patch: Partial<AgentInputMapping>) {
  if (row.mapping)
    emit('setMapping', { ...row.mapping, ...patch })
}
</script>

<template>
  <section v-if="rows.length > 0" :aria-labelledby="`${ids}-vars`">
    <div class="flex items-baseline justify-between gap-2">
      <h4 :id="`${ids}-vars`" class="font-medium text-highlighted" :class="compact ? 'text-xs' : 'text-sm'">
        {{ title }}
      </h4>
      <span class="text-xs text-muted tabular-nums">{{ mappedCount }} of {{ rows.length }} mapped</span>
    </div>
    <p class="mt-0.5 text-muted" :class="compact ? 'text-xs' : 'text-sm'">
      {{ description }}
    </p>

    <ul class="divide-y divide-default rounded-lg border border-default" :class="compact ? 'mt-2' : 'mt-3'">
      <li
        v-for="row in rows"
        :key="row.variable"
        class="grid items-center gap-2 @xl:grid-cols-[minmax(6rem,10rem)_auto_11rem_minmax(0,1fr)]"
        :class="compact ? 'px-2.5 py-2' : 'px-3 py-2.5'"
        @mouseenter="emit('highlight', row.variable)"
        @mouseleave="emit('highlight', null)"
        @focusin="emit('highlight', row.variable)"
        @focusout="emit('highlight', null)"
      >
        <code class="w-fit max-w-full truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="row.variable">{{ row.variable }}</code>
        <UIcon name="i-ph-arrow-right-bold" class="hidden size-3.5 shrink-0 text-dimmed @xl:block" aria-hidden="true" />

        <USelect
          :model-value="row.mapping?.source"
          :items="sourceItems(row.mapping)"
          placeholder="Choose a source"
          size="sm"
          class="w-full"
          :aria-label="`Source for ${row.variable}`"
          :color="row.mapping ? 'neutral' : 'warning'"
          :highlight="!row.mapping"
          @update:model-value="(source) => chooseSource(row.variable, source as AgentInputMapping['source'])"
        />

        <div class="min-w-0">
          <USelect
            v-if="row.mapping?.source === 'dataset'"
            :model-value="row.mapping.sourceColumn"
            :items="columnItems"
            :disabled="columnItems.length === 0"
            :placeholder="columnItems.length === 0 ? 'Choose a dataset first' : 'Choose a column'"
            size="sm"
            class="w-full"
            :color="row.mapping.sourceColumn ? 'neutral' : 'warning'"
            :highlight="!row.mapping.sourceColumn"
            :aria-label="`Dataset column for ${row.variable}`"
            @update:model-value="(value: string) => patchMapping(row, { sourceColumn: value })"
          />
          <div v-else-if="row.mapping?.source === 'agent'" class="flex min-w-0 gap-2">
            <USelect
              :model-value="mappingSource(row.mapping)"
              :items="upstreamItems"
              placeholder="Choose an agent"
              size="sm"
              class="min-w-0 flex-1"
              :color="mappingSource(row.mapping) === undefined ? 'warning' : 'neutral'"
              :highlight="mappingSource(row.mapping) === undefined"
              :aria-label="`Agent output for ${row.variable}`"
              @update:model-value="(value: string) => patchMapping(row, { sourceStep: value, sourceAgentId: undefined, sourceOutput: 'output', sourcePath: '' })"
            />
            <ExperimentsOutputPathSelect
              :model-value="row.mapping.sourcePath"
              :step-key="mappingSource(row.mapping)"
              whole-label="Whole output"
              :with-lists="withLists"
              class="min-w-0 flex-1"
              :aria-label="`Field of the output for ${row.variable}`"
              @update:model-value="(value: string | undefined) => patchMapping(row, { sourcePath: value ?? '' })"
            />
          </div>
          <UInput
            v-else-if="row.mapping?.source === 'static'"
            :model-value="row.mapping.staticValue"
            :placeholder="staticPlaceholder"
            size="sm"
            class="w-full"
            :color="isComplete(row.mapping) ? 'neutral' : 'warning'"
            :highlight="!isComplete(row.mapping)"
            :aria-label="`${staticLabel} for ${row.variable}`"
            @update:model-value="(value: string | number) => patchMapping(row, { staticValue: String(value) })"
          />
          <p v-else class="inline-flex items-center gap-1.5 text-xs text-warning">
            <UIcon name="i-ph-warning-bold" class="size-3.5 shrink-0" aria-hidden="true" />
            Not mapped yet
          </p>
        </div>
      </li>
    </ul>
  </section>
</template>
