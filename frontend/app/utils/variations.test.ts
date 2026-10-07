import type { AgentConfiguration, PromptVersion, VariationDraft } from '~/types'
import { describe, expect, it } from 'vitest'
import { addedVariables, addedVariablesByAgent, unmappedAddedCount } from './variations'

const version = (id: number, variables: string[]) => ({ id, variables: JSON.stringify(variables) }) as PromptVersion

const versions = [version(1, ['text']), version(2, ['text', 'context']), version(3, ['question', 'context'])]

const config: AgentConfiguration = {
  prompt_version_id: 1,
  input_mappings: [{ variable: 'text', source: 'dataset', sourceColumn: 'text' }],
}

const draft = (extras: number[], field: VariationDraft['field'] = 'prompt_version_id'): VariationDraft => ({ agent_id: 7, field, extras })

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

describe('addedVariablesByAgent', () => {
  it('groups them by agent and leaves out agents with nothing to map', () => {
    const drafts = [draft([2]), { agent_id: 8, field: 'prompt_version_id' as const, extras: [1] }]
    expect(addedVariablesByAgent(drafts, { 7: config, 8: config }, versions)).toEqual({ 7: ['context'] })
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
