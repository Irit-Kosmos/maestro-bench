import { describe, expect, it } from 'vitest'
import { hasFailures, runsSummary } from './executions'

describe('hasFailures', () => {
  it('counts an execution that failed, or went on with failed rows', () => {
    expect(hasFailures({ status: 'failed', rows_failed: 0 })).toBe(true)
    expect(hasFailures({ status: 'completed', rows_failed: 2 })).toBe(true)
    expect(hasFailures({ status: 'running', rows_failed: 1 })).toBe(true)
  })

  it('leaves out a clean one and a cancelled one, even with failed rows behind it', () => {
    expect(hasFailures({ status: 'completed', rows_failed: 0 })).toBe(false)
    expect(hasFailures({ status: 'cancelled', rows_failed: 3 })).toBe(false)
    expect(hasFailures({ status: 'interrupted', rows_failed: 3 })).toBe(false)
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
