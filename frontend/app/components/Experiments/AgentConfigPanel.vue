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
import type { Agent, AgentInputMapping, Model, PromptVersion } from '~/types'

// Side panel of the graph view: the same settings as the list, for the selected node
defineProps<{
  agent: Agent | null
  /** The step's name, when it is not its agent's */
  label?: string
  config: Record<string, any> | undefined
  models: Model[]
  allPromptVersions: PromptVersion[]
  datasetHeaders: readonly string[]
  upstreamSteps: readonly StepRef[]
}>()

const emit = defineEmits<{
  updateConfig: [field: string, value: any]
  updateInputMapping: [mapping: AgentInputMapping]
  remove: []
  close: []
  reset: []
  openPromptDetails: [promptVersionId: number]
}>()

// Opening the panel moves the focus to it: its heading is where a keyboard user starts reading
const heading = ref<HTMLElement>()
onMounted(() => heading.value?.focus({ preventScroll: true }))

// Delete or Backspace removes the agent, as on the canvas: opening the panel took the focus away from the node.
// Not from a field, nor from a menu or a list of options, which use these keys themselves
function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Delete' && e.key !== 'Backspace')
    return
  if (e.metaKey || e.ctrlKey || e.altKey)
    return
  const el = e.target as HTMLElement
  if (el.closest('input, textarea, select, [contenteditable], [role="listbox"], [role="menu"], [role="combobox"]'))
    return
  e.preventDefault()
  emit('remove')
}
</script>

<template>
  <div class="flex h-full w-80 max-w-full shrink-0 flex-col border-l border-default bg-default" @keydown="onKeydown">
    <header class="flex items-start justify-between gap-2 border-b border-default px-3 py-2.5">
      <div class="min-w-0">
        <h4 ref="heading" tabindex="-1" class="truncate text-sm font-semibold text-highlighted outline-none">
          {{ label || agent?.name || 'Configure agent' }}
        </h4>
        <p v-if="agent?.description" class="mt-0.5 text-xs text-muted line-clamp-2">
          {{ agent.description }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-0.5">
        <UTooltip text="Remove from the flow" :kbds="['backspace']">
          <UButton
            variant="ghost"
            size="xs"
            icon="i-ph-trash-bold"
            color="neutral"
            class="hover:text-error focus-visible:text-error"
            aria-label="Remove from the flow"
            aria-keyshortcuts="Backspace Delete"
            @click="emit('remove')"
          />
        </UTooltip>
        <UButton
          variant="ghost"
          size="xs"
          icon="i-ph-x-bold"
          color="neutral"
          aria-label="Close panel"
          @click="emit('close')"
        />
      </div>
    </header>

    <div v-if="agent" class="flex-1 overflow-y-auto p-3">
      <ExperimentsAggregatorSettings
        v-if="agent.kind === 'aggregator'"
        :config="config"
        :dataset-headers="datasetHeaders"
        :upstream-steps="upstreamSteps"
        compact
        @update="(field, value) => emit('updateConfig', field, value)"
        @set-mapping="mapping => emit('updateInputMapping', mapping)"
      />
      <ExperimentsAgentSettings
        v-else
        :config="config"
        :models="models"
        :prompt-versions="allPromptVersions"
        :dataset-headers="datasetHeaders"
        :upstream-steps="upstreamSteps"
        compact
        @update="(field, value) => emit('updateConfig', field, value)"
        @set-mapping="mapping => emit('updateInputMapping', mapping)"
        @open-prompt-details="id => emit('openPromptDetails', id)"
      />

      <div class="mt-4 flex flex-col gap-2 border-t border-default pt-3">
        <USwitch
          :model-value="config?.is_active ?? true"
          label="Run this agent"
          size="xs"
          @update:model-value="(value: boolean) => emit('updateConfig', 'is_active', value)"
        />
        <div>
          <UButton variant="ghost" color="neutral" size="xs" icon="i-ph-arrow-counter-clockwise-bold" @click="emit('reset')">
            Reset to agent defaults
          </UButton>
        </div>
      </div>
    </div>
  </div>
</template>
