// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import type { InjectionKey } from 'vue'
import type { AgentInputMapping, FormulaOutput } from '~/types'
import { watchDebounced } from '@vueuse/core'

export interface FormulaCheck {
  /** One message per formula, null when it is valid */
  errors: (string | null)[]
  /** Whether each error is about the output's name rather than its formula */
  name_invalid: boolean[]
  variables: string[]
}

/** Prompt version each step of the experiment uses, by step key: provided by the agents step */
export const AGENT_PROMPT_VERSIONS: InjectionKey<Ref<Record<string, number | undefined>>> = Symbol('agentPromptVersions')

export interface AggregatorPreview {
  execution_id: number | null
  experiment_name: string | null
  /** False when no run used the experiment's prompt versions, and the rows come from other versions */
  versions_match: boolean
  rows: { row_index: number | null, inputs: Record<string, unknown>, output: Record<string, unknown> | null, error: string | null }[]
}

// Backend verdicts by formulas, shared so the issues list sees what the editor checked
const checks = reactive(new Map<string, FormulaCheck>())

function keyOf(formulas: readonly FormulaOutput[]) {
  return JSON.stringify(formulas.map(f => [f.name, f.formula]))
}

/** The backend's errors for these formulas, once checked */
export function formulaErrorsOf(formulas: readonly FormulaOutput[] | undefined): FormulaCheck | undefined {
  return checks.get(keyOf(formulas ?? []))
}

/**
 * Keeps an aggregator's formulas checked by the backend while they are edited,
 * and previews them on the rows of a past execution.
 */
export function useFormulaCheck(
  formulas: Ref<FormulaOutput[] | undefined>,
  mappings: Ref<AgentInputMapping[] | undefined>,
) {
  const { $api } = useNuxtApp()
  const promptVersions = inject(AGENT_PROMPT_VERSIONS, ref<Record<string, number | undefined>>({}))

  const check = computed(() => formulaErrorsOf(formulas.value))

  watchDebounced(formulas, async (value) => {
    const list = value ?? []
    const key = keyOf(list)
    if (list.length === 0 || checks.has(key))
      return
    try {
      checks.set(key, await $api<FormulaCheck>('/aggregators/check', { method: 'POST', body: { formulas: list } }))
    }
    catch (error) {
      console.error('Error checking formulas:', error)
    }
  }, { debounce: 300, deep: true, immediate: true })

  const preview = ref<AggregatorPreview | null>(null)
  const previewing = ref(false)

  async function runPreview() {
    previewing.value = true
    try {
      preview.value = await $api<AggregatorPreview>('/aggregators/preview', {
        method: 'POST',
        body: { formulas: formulas.value ?? [], input_mappings: mappings.value ?? [], prompt_versions: promptVersions.value },
      })
    }
    catch (error) {
      console.error('Error previewing formulas:', error)
      preview.value = null
    }
    finally {
      previewing.value = false
    }
  }

  return { check, preview, previewing, runPreview }
}

// Paths seen in an agent's recent outputs, fetched once per agent
export interface AgentOutputPaths {
  /** Single values */
  paths: string[]
  /** Lists of values, like a score distribution */
  list_paths: string[]
}

const outputPaths = reactive(new Map<string, AgentOutputPaths>())
const pendingPaths = new Set<string>()

export function useAgentOutputPaths() {
  const { $api } = useNuxtApp()

  /** Paths seen in the agent's runs with this prompt version (any version when unknown); null while loading */
  function pathsOf(agentId: number | undefined, promptVersionId?: number): AgentOutputPaths | null {
    if (agentId === undefined)
      return { paths: [], list_paths: [] }
    const key = `${agentId}:${promptVersionId ?? ''}`
    if (!outputPaths.has(key) && !pendingPaths.has(key)) {
      pendingPaths.add(key)
      $api<AgentOutputPaths>(`/agents/${agentId}/output-paths`, { query: promptVersionId ? { prompt_version_id: promptVersionId } : {} })
        .then(response => outputPaths.set(key, { paths: response.paths, list_paths: response.list_paths ?? [] }))
        .catch((error) => {
          // Let a later render try again
          pendingPaths.delete(key)
          console.error('Error loading output paths:', error)
        })
    }
    return outputPaths.get(key) ?? null
  }

  return { pathsOf }
}
