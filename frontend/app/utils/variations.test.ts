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

import type { AgentConfiguration, PromptVersion, VariationDraft } from '~/types'
import { describe, expect, it } from 'vitest'
import { addedVariables, addedVariablesByStep, formSignature, resolveVariations, unmappedAddedCount, variationIssues } from './variations'

const version = (id: number, variables: string[]) => ({ id, variables: JSON.stringify(variables) }) as PromptVersion

const versions = [version(1, ['text']), version(2, ['text', 'context']), version(3, ['question', 'context'])]

const config: AgentConfiguration = {
  prompt_version_id: 1,
  input_mappings: [{ variable: 'text', source: 'dataset', sourceColumn: 'text' }],
}

const draft = (extras: number[], field: VariationDraft['field'] = 'prompt_version_id'): VariationDraft => ({ step_key: '7', field, extras })

describe('addedVariables', () => {
  it('lists the variables the current prompt lacks, once each', () => {
    expect(addedVariables(draft([2, 3]), config, versions)).toEqual(['context', 'question'])
  })

  it('is empty when the prompts use the same variables', () => {
    expect(addedVariables(draft([1]), config, versions)).toEqual([])
  })

  it('only concerns prompt variations', () => {
    expect(addedVariables(draft([2], 'model_id'), config, versions)).toEqual([])
  })
})

describe('addedVariablesByStep', () => {
  it('groups them by step and leaves out steps with nothing to map', () => {
    const drafts = [draft([2]), { step_key: '8', field: 'prompt_version_id' as const, extras: [1] }]
    expect(addedVariablesByStep(drafts, { 7: config, 8: config }, versions)).toEqual({ 7: ['context'] })
  })

  it('keeps the two steps of one agent apart', () => {
    const drafts = [draft([2]), { step_key: '7#2', field: 'prompt_version_id' as const, extras: [3] }]
    const other: AgentConfiguration = { prompt_version_id: 2 }
    expect(addedVariablesByStep(drafts, { '7': config, '7#2': other }, versions)).toEqual({ '7': ['context'], '7#2': ['question'] })
  })
})

describe('resolveVariations', () => {
  it('runs the base value of each step then what is added, so two steps of an agent are two axes', () => {
    const configs: Record<string, AgentConfiguration> = { '7': { model_id: 1 }, '7#2': { model_id: 5 } }
    const drafts: VariationDraft[] = [
      { step_key: '7', field: 'model_id', extras: [2] },
      { step_key: '7#2', field: 'model_id', extras: [6, 5] },
    ]
    expect(resolveVariations(drafts, configs)).toEqual([
      { step_key: '7', field: 'model_id', values: [1, 2] },
      { step_key: '7#2', field: 'model_id', values: [5, 6] },
    ])
  })
})

describe('variationIssues', () => {
  it('refuses the same field of the same step twice, not of two steps of one agent', () => {
    expect(variationIssues([draft([1], 'model_id'), { step_key: '7#2', field: 'model_id', extras: [2] }])).toEqual([])
    expect(variationIssues([draft([1], 'model_id'), draft([2], 'model_id')])).toHaveLength(1)
  })
})

describe('formSignature', () => {
  const sampling = { sampling_type: 'all' }

  it('tells a pipeline that runs an agent twice from one that runs it once', () => {
    const once = formSignature(1, sampling, { 7: { model_id: 1, execution_order: 1 } })
    const twice = formSignature(1, sampling, { '7': { model_id: 1, execution_order: 1 }, '7#2': { model_id: 1, execution_order: 2 } })
    expect(twice).not.toBe(once)
  })

  it('reads a mapping saved with an agent id like one with the step', () => {
    const mapped = (source: object) => ({ 8: { execution_order: 2, input_mappings: [{ variable: 'a', source: 'agent' as const, ...source }] } })
    expect(formSignature(1, sampling, mapped({ sourceAgentId: 7 }))).toBe(formSignature(1, sampling, mapped({ sourceStep: '7' })))
  })
})

describe('unmappedAddedCount', () => {
  it('counts the variables without a complete mapping', () => {
    const added = { 7: ['context', 'question'] }
    expect(unmappedAddedCount(added, { 7: config })).toBe(2)
    const mapped: AgentConfiguration = {
      ...config,
      input_mappings: [...config.input_mappings!, { variable: 'context', source: 'dataset', sourceColumn: 'ctx' }, { variable: 'question', source: 'dataset' }],
    }
    // "question" has a source but no column yet
    expect(unmappedAddedCount(added, { 7: mapped })).toBe(1)
  })
})
