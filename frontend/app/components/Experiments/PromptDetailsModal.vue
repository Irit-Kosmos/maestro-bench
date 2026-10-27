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
import type { PromptVersion } from '~/types'

// A prompt version, read-only: where it comes from, its variables, and the text as written.
// Pointing at a variable picks it out in the text, the same way the mappings do in the agent panel.
const props = defineProps<{
  promptVersionDetails: PromptVersion | null
}>()

const open = defineModel<boolean>('isOpen', { default: false })

const { formatDate } = useUIHelpers()

const name = computed(() => props.promptVersionDetails?.prompt?.name ?? 'Prompt')
// "1.2" reads as a version once it has a "v"; "v2" or "beta" already do
const version = computed(() => {
  const label = props.promptVersionDetails?.version ?? ''
  return /^\d/.test(label) ? `v${label}` : label
})
const variables = computed(() => parseVariables(props.promptVersionDetails?.variables || ''))
const isEmpty = computed(() => !props.promptVersionDetails?.system_prompt && !props.promptVersionDetails?.user_prompt)

// Variable under the pointer, picked out in the text
const active = ref<string | null>(null)
watch(open, () => active.value = null)
</script>

<template>
  <UModal
    v-model:open="open"
    :title="`${name} ${version}`"
    description="Prompt version details"
    :ui="{ content: 'sm:max-w-2xl' }"
  >
    <template #content>
      <div v-if="promptVersionDetails" class="flex max-h-[min(80vh,46rem)] min-h-0 flex-col">
        <header class="flex shrink-0 items-start justify-between gap-3 border-b border-default py-2.5 ps-4 pe-2.5">
          <div class="min-w-0">
            <h2 class="flex items-baseline gap-2 text-sm font-medium text-highlighted">
              <span class="truncate">{{ name }}</span>
              <span class="shrink-0 font-mono text-xs font-normal text-muted">{{ version }}</span>
            </h2>
            <p class="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted">
              <template v-if="promptVersionDetails.is_default">
                <span class="inline-flex items-center gap-1 text-default">
                  <UIcon name="i-ph-star-fill" class="size-3 text-warning" aria-hidden="true" />
                  Default
                </span>
                <span aria-hidden="true">·</span>
              </template>
              <template v-if="!promptVersionDetails.is_active">
                <span>Inactive</span>
                <span aria-hidden="true">·</span>
              </template>
              <span>Created {{ formatDate(promptVersionDetails.created_at) }}</span>
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-0.5">
            <UButton
              :to="`/prompts/${promptVersionDetails.prompt_id}?v=${promptVersionDetails.id}`"
              target="_blank"
              icon="i-ph-arrow-up-right-bold"
              color="neutral"
              variant="ghost"
              size="sm"
              square
              aria-label="Open in Prompts"
            />
            <UButton
              icon="i-ph-x-bold"
              color="neutral"
              variant="ghost"
              size="sm"
              square
              aria-label="Close"
              @click="() => { open = false }"
            />
          </div>
        </header>

        <div class="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
          <p v-if="promptVersionDetails.prompt?.description" class="text-sm text-toned text-pretty">
            {{ promptVersionDetails.prompt.description }}
          </p>

          <PromptContentDisplay
            v-if="promptVersionDetails.system_prompt"
            label="System prompt"
            :content="promptVersionDetails.system_prompt"
            :variables="variables"
            :active="active"
          />
          <PromptContentDisplay
            v-if="promptVersionDetails.user_prompt"
            label="User prompt"
            :content="promptVersionDetails.user_prompt"
            :variables="variables"
            :active="active"
          />

          <p v-if="isEmpty" class="text-sm text-muted">
            This version has no prompt text yet.
          </p>

          <PromptVariablesDisplay
            v-if="variables.length"
            v-model:active="active"
            :variables="promptVersionDetails.variables"
          />

          <PromptContentDisplay
            v-if="promptVersionDetails.notes"
            label="Notes"
            :content="promptVersionDetails.notes"
            type="text"
          />
        </div>
      </div>
    </template>
  </UModal>
</template>
