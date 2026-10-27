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
import type { AgentConfiguration, AgentInputMapping, Model, PromptVersion } from '~/types'

// The settings of one agent in an experiment: prompt, model, sampling and where each prompt variable gets its value.
// Shared by the list rows and the graph's side panel so both edit the same thing the same way.
const props = defineProps<{
  config: AgentConfiguration | undefined
  models: readonly Model[]
  promptVersions: readonly PromptVersion[]
  datasetHeaders: readonly string[]
  /** Steps whose output this one may read, nearest last */
  upstreamSteps: readonly StepRef[]
  /** Smaller type and controls, for a side panel */
  compact?: boolean
}>()

const emit = defineEmits<{
  update: [field: 'prompt_version_id' | 'model_id' | 'temperature' | 'max_tokens', value: number | undefined]
  setMapping: [mapping: AgentInputMapping]
  openPromptDetails: [promptVersionId: number]
}>()

const selectedModel = computed(() => props.models.find(m => m.id === props.config?.model_id))

// Empty fields fall back to the model's own defaults, so say which
const temperaturePlaceholder = computed(() => selectedModel.value?.default_temperature?.toString() ?? 'Model default')
const maxTokensPlaceholder = computed(() => selectedModel.value?.default_max_tokens?.toString() ?? 'Model default')

function toNumber(value: string | number | undefined, parse: (s: string) => number) {
  if (value === '' || value === undefined)
    return undefined
  const parsed = parse(String(value))
  return Number.isNaN(parsed) ? undefined : parsed
}

// --- Variables ---

const promptVersion = computed(() => props.promptVersions.find(v => v.id === props.config?.prompt_version_id))
const variables = computed(() => parsePromptVariables(promptVersion.value?.variables))

// The variable under the pointer in the mappings, picked out in the prompt below
const highlighted = ref<string | null>(null)
</script>

<template>
  <div class="@container flex flex-col" :class="compact ? 'gap-4' : 'gap-5'">
    <div class="grid" :class="compact ? 'grid-cols-2 gap-3' : 'gap-4 @md:grid-cols-2 @3xl:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]'">
      <UFormField label="Prompt version" required :size="compact ? 'sm' : undefined" :class="compact && 'col-span-2'">
        <template v-if="config?.prompt_version_id" #hint>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            icon="i-ph-eye-bold"
            class="-my-1"
            @click="emit('openPromptDetails', config.prompt_version_id!)"
          >
            View
          </UButton>
        </template>
        <PromptsSelect
          :model-value="config?.prompt_version_id"
          :prompt-versions="promptVersions"
          class="w-full"
          @update:model-value="(value) => emit('update', 'prompt_version_id', (value as number | undefined) ?? undefined)"
        />
      </UFormField>

      <UFormField label="Model" required :size="compact ? 'sm' : undefined" :class="compact && 'col-span-2'">
        <ModelsSelect
          :model-value="config?.model_id"
          :models="models"
          class="w-full"
          @update:model-value="(value) => emit('update', 'model_id', (value as number | undefined) ?? undefined)"
        />
      </UFormField>

      <UFormField label="Temperature" :size="compact ? 'sm' : undefined">
        <UInput
          :model-value="config?.temperature?.toString() ?? ''"
          type="number"
          inputmode="decimal"
          step="0.1"
          min="0"
          max="1"
          :placeholder="temperaturePlaceholder"
          class="w-full tabular-nums"
          @update:model-value="(value: string | number) => emit('update', 'temperature', toNumber(value, Number.parseFloat))"
        />
      </UFormField>

      <UFormField label="Max tokens" :size="compact ? 'sm' : undefined">
        <UInput
          :model-value="config?.max_tokens?.toString() ?? ''"
          type="number"
          inputmode="numeric"
          min="100"
          :placeholder="maxTokensPlaceholder"
          class="w-full tabular-nums"
          @update:model-value="(value: string | number) => emit('update', 'max_tokens', toNumber(value, s => Number.parseInt(s, 10)))"
        />
      </UFormField>
    </div>

    <ExperimentsVariableMappings
      :variables="variables"
      :mappings="config?.input_mappings"
      :dataset-headers="datasetHeaders"
      :upstream-steps="upstreamSteps"
      title="Prompt variables"
      description="Where each variable of the prompt gets its value for every row."
      :compact="compact"
      @set-mapping="mapping => emit('setMapping', mapping)"
      @highlight="variable => highlighted = variable"
    />

    <ExperimentsPromptPreview
      :version="promptVersion"
      :variables="variables"
      :mappings="config?.input_mappings"
      :upstream-steps="upstreamSteps"
      :active="highlighted"
      :compact="compact"
    />
  </div>
</template>
