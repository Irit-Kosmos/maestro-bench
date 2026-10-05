import type { ExecutionListItem } from '~/types'
import { describe, expect, it } from 'vitest'
import { executionExperimentFilter, executionFailuresFilter, executionModelsFilter, hasFailures, isAnalyzable, runsSummary } from './executions'
import { buildFilterDefinitions } from './filters'

function execution(fields: Partial<ExecutionListItem> = {}): ExecutionListItem {
  return {
    id: 1,
    experiment_id: 1,
    experiment_name: 'Run',
    batch_id: null,
    batch_name: null,
    dataset_name: null,
    status: 'completed',
    started_at: '2026-10-02T11:00:00',
    completed_at: null,
    duration_seconds: null,
    rows_total: null,
    rows_done: 0,
    rows_failed: 0,
    row_count: null,
    has_results: true,
    total_tokens: null,
    total_cost_usd: null,
    agents: [],
    ...fields,
  }
}

describe('hasFailures', () => {
  it('counts an execution that failed, or went on with failed rows', () => {
    expect(hasFailures(execution({ status: 'failed' }))).toBe(true)
    expect(hasFailures(execution({ status: 'completed', rows_failed: 2 }))).toBe(true)
    expect(hasFailures(execution({ status: 'running', rows_failed: 1 }))).toBe(true)
  })

  it('leaves out a clean one and a cancelled one, even with failed rows behind it', () => {
    expect(hasFailures(execution({ status: 'completed' }))).toBe(false)
    expect(hasFailures(execution({ status: 'cancelled', rows_failed: 3 }))).toBe(false)
    expect(hasFailures(execution({ status: 'interrupted', rows_failed: 3 }))).toBe(false)
  })
})

describe('isAnalyzable', () => {
  it('needs a completed execution with its results', () => {
    expect(isAnalyzable(execution())).toBe(true)
    expect(isAnalyzable(execution({ has_results: false }))).toBe(false)
    expect(isAnalyzable(execution({ status: 'failed' }))).toBe(false)
    expect(isAnalyzable(execution({ status: 'running', has_results: false }))).toBe(false)
  })
})

describe('executionFailuresFilter', () => {
  it('tells the failures from the clean ones', () => {
    const items = [execution({ status: 'failed' }), execution({ id: 2 })]
    const [definition] = buildFilterDefinitions(items, [executionFailuresFilter()])
    expect(definition!.options.map(option => [option.label, option.count])).toEqual([['Failed or with failed rows', 1], ['No failures', 1]])
  })
})

describe('executionModelsFilter', () => {
  it('lists a model once per execution, however many agents use it', () => {
    const agent = (model: string) => ({ agent_id: 1, name: 'a', model, provider: 'openai', prompt: 'p', prompt_version: '1' })
    const items = [execution({ agents: [agent('m-a'), agent('m-a'), agent('m-b')] })]
    const [definition] = buildFilterDefinitions(items, [executionModelsFilter()])
    expect(definition!.options.map(option => [option.label, option.count])).toEqual([['m-a', 1], ['m-b', 1]])
  })
})

describe('executionExperimentFilter', () => {
  it('reads an experiment by its name', () => {
    const items = [execution({ experiment_id: 7, experiment_name: 'Grade answers' })]
    const [definition] = buildFilterDefinitions(items, [executionExperimentFilter(() => items)])
    expect(definition!.options.map(option => option.label)).toEqual(['Grade answers'])
  })
})

describe('runsSummary', () => {
  it('says nothing when all is well', () => {
    expect(runsSummary([{ status: 'completed', rows_failed: 0 }, { status: 'pending' }, { status: 'cancelled', rows_failed: 3 }])).toEqual([])
  })

  it('counts the runs going and the ones that went wrong, failed rows included', () => {
    const parts = runsSummary([
      { status: 'running' },
      { status: 'failed' },
      { status: 'completed', rows_failed: 2 },
      { status: 'completed', rows_failed: 0 },
    ])
    expect(parts.map(part => part.label)).toEqual(['1 running', '2 failed'])
  })
})
