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
import type { AgentExecutionSnapshot } from '~/types'

// Read-only node of the execution graph: what the agent ran with, as recorded when the run started
const props = defineProps<{
  data: { snapshot: AgentExecutionSnapshot, step: number }
  selected?: boolean
}>()

const snapshot = computed(() => props.data.snapshot)
const formulas = computed(() => parseSnapshotFormulas(snapshot.value))
const aggregator = computed(() => snapshot.value.kind === 'aggregator')
const variables = computed(() => aggregator.value
  ? formulaVariables(formulas.value)
  : parsePromptVariables(snapshot.value.final_variables))
</script>

<template>
  <GraphNodeCard
    :kicker="aggregator ? `Step ${data.step} · Aggregator` : `Step ${data.step}`"
    :icon="aggregator ? 'i-ph-function-bold' : 'i-ph-ghost-bold'"
    :accent="aggregator"
    :title="snapshot.agent_name_snapshot"
    :selected="selected"
  >
    <template v-if="aggregator">
      <div v-for="f in formulas" :key="f.name" class="flex items-center gap-1.5 text-xs text-toned">
        <UIcon name="i-ph-function-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
        <span class="truncate font-mono" :title="`${f.name} = ${f.formula}`">{{ f.name }} = {{ f.formula }}</span>
      </div>
    </template>
    <template v-else>
      <div class="flex items-center gap-1.5 text-xs text-toned">
        <UIcon name="i-ph-chat-text-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
        <span class="truncate" :title="`${snapshot.prompt_name_snapshot} v${snapshot.prompt_version_snapshot}`">
          {{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}
        </span>
      </div>
      <ModelsLabel :name="snapshot.model_name_snapshot" :provider="snapshot.model_provider_snapshot" class="text-xs text-toned" />
    </template>

    <div v-if="variables.length > 0" class="flex flex-wrap gap-1 border-t border-default pt-2">
      <span
        v-for="variable in variables"
        :key="variable"
        class="rounded-md border border-default bg-default px-1.5 py-0.5 font-mono text-[11px] leading-none text-toned"
      >{{ variable }}</span>
    </div>
  </GraphNodeCard>
</template>
