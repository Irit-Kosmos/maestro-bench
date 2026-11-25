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
import type { ExecutionRow } from '~/types'
import { cellText } from '~/composables/useDatasetEditor'

// One row of an execution in full: why it failed, the dataset row that went in,
// and what every agent sent and returned. Shared by the analysis and failure panels.
defineProps<{
  row: ExecutionRow
  /** Column marked as the ground truth (analyses) */
  truthColumn?: string
  /** Agent marked as the one being analysed (analyses) */
  markedAgent?: string
}>()

const uid = useId()

// What an aggregator computed from: "langue = 3 · contenu = 4"
function inputsText(inputs: Record<string, unknown> | null | undefined): string {
  return Object.entries(inputs ?? {}).map(([k, v]) => `${k} = ${formatFormulaValue(v)}`).join(' · ')
}

function outputText(output: unknown): string {
  if (typeof output === 'string')
    return output
  return output === null || output === undefined ? '' : JSON.stringify(output, null, 2)
}

// Chat content is a string, or a list of parts for multimodal models
function messageText(content: unknown): string {
  if (typeof content === 'string')
    return content
  if (Array.isArray(content))
    return content.map(part => (part as { text?: unknown })?.text ?? JSON.stringify(part)).join('\n')
  return outputText(content)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <slot name="before" />

    <!-- An agent that failed says so on its own output below: the row's error would only repeat it -->
    <UAlert
      v-if="row.error && !row.agents.some(agent => agent.error)"
      color="error"
      variant="subtle"
      icon="i-ph-x-circle-bold"
      :title="row.error"
      :ui="{ title: 'whitespace-pre-wrap break-words' }"
    />

    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-highlighted">
        Dataset row
      </h3>
      <div v-for="(value, key) in row.input_data" :key="key">
        <label
          :for="`${uid}-input-${key}`"
          class="flex items-center gap-2 mb-1 text-xs font-medium font-mono text-muted"
        >
          {{ key }}
          <UBadge
            v-if="key === truthColumn"
            label="ground truth"
            color="primary"
            variant="soft"
            size="sm"
            class="font-sans"
          />
        </label>
        <UTextarea
          :id="`${uid}-input-${key}`"
          :model-value="cellText(value)"
          readonly
          autoresize
          :rows="1"
          :maxrows="14"
          class="w-full"
          :ui="{ base: 'text-muted' }"
        />
      </div>
      <p v-if="Object.keys(row.input_data).length === 0" class="text-sm text-muted">
        The row’s data wasn’t kept: it failed before reaching the agents.
      </p>
    </section>

    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-highlighted">
        Agent outputs
      </h3>
      <div v-for="(agent, i) in row.agents" :key="`${agent.name}-${i}`" class="flex flex-col gap-1">
        <label
          :for="`${uid}-agent-${i}`"
          class="flex items-center gap-2 text-xs font-medium font-mono text-muted"
        >
          {{ agent.name }}
          <UBadge
            v-if="markedAgent && agent.name === markedAgent"
            label="analysed"
            color="primary"
            variant="soft"
            size="sm"
            class="font-sans"
          />
        </label>
        <p
          v-if="agent.kind === 'aggregator' && inputsText(agent.inputs)"
          class="flex items-center gap-1.5 font-mono text-xs text-toned"
        >
          <UIcon name="i-ph-function-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
          <span class="min-w-0">{{ inputsText(agent.inputs) }}</span>
        </p>
        <UAlert
          v-if="agent.error"
          :id="`${uid}-agent-${i}`"
          color="error"
          variant="subtle"
          icon="i-ph-x-circle-bold"
          :title="agent.error"
          :ui="{ title: 'whitespace-pre-wrap break-words' }"
        />
        <UTextarea
          v-else
          :id="`${uid}-agent-${i}`"
          :model-value="outputText(agent.output)"
          readonly
          autoresize
          :rows="1"
          :maxrows="14"
          class="w-full"
          :ui="{ base: 'text-muted font-mono' }"
        />

        <!-- What the model was actually asked: folded, it is long and only needed to understand a failure -->
        <UCollapsible
          v-if="agent.messages_sent?.length"
          class="group/messages"
          :ui="{ content: 'data-[state=open]:animate-[collapsible-down_200ms_var(--ease-out)] data-[state=closed]:animate-[collapsible-up_150ms_var(--ease-out)] motion-reduce:animate-none' }"
        >
          <button
            type="button"
            class="-ms-1 inline-flex items-center gap-1 rounded-sm px-1 py-0.5 text-xs text-muted outline-none hover:text-highlighted focus-visible:outline-2 focus-visible:outline-inverted"
          >
            <UIcon
              name="i-ph-caret-right-bold"
              class="size-3 shrink-0 transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none group-data-[state=open]/messages:rotate-90"
              aria-hidden="true"
            />
            Messages sent
            <span class="tabular-nums text-dimmed">{{ agent.messages_sent.length }}</span>
          </button>
          <template #content>
            <ol class="flex flex-col gap-2 pt-1.5">
              <li v-for="(message, m) in agent.messages_sent" :key="m" class="rounded-md bg-elevated/60 px-3 py-2">
                <p class="mb-1 text-[0.6875rem] font-medium uppercase tracking-wide text-dimmed">
                  {{ message.role }}
                </p>
                <pre class="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-toned">{{ messageText(message.content) }}</pre>
              </li>
            </ol>
          </template>
        </UCollapsible>
      </div>
      <p v-if="!row.agents.length" class="text-sm text-muted">
        No agent ran on this row.
      </p>
    </section>
  </div>
</template>
