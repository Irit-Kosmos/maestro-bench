import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { buildFilterDefinitions, matchesSpecs } from './filters'
import { dateFilter, dateRanges, failuresFilter, filterByTag, runsFilter, statusFilter, tagsFilter } from './filterSpecs'

const NOW = Date.parse('2026-10-02T12:00:00Z')
const HOUR = 60 * 60 * 1000
const DAY = 24 * HOUR
const ago = (ms: number) => new Date(NOW - ms).toISOString()

describe('dateRanges', () => {
  it('puts a date in every window it falls in', () => {
    expect(dateRanges(ago(2 * HOUR), NOW)).toEqual(['day', 'week', 'month', 'quarter'])
    expect(dateRanges(ago(3 * DAY), NOW)).toEqual(['week', 'month', 'quarter'])
    expect(dateRanges(ago(20 * DAY), NOW)).toEqual(['month', 'quarter'])
    expect(dateRanges(ago(60 * DAY), NOW)).toEqual(['quarter'])
  })

  it('calls anything older than a quarter "older"', () => {
    expect(dateRanges(ago(120 * DAY), NOW)).toEqual(['older'])
  })

  it('reads the API\'s offset-less datetimes as UTC', () => {
    expect(dateRanges('2026-10-02T11:00:00', NOW)).toContain('day')
  })

  it('has nothing to say about an unreadable date', () => {
    expect(dateRanges('not a date', NOW)).toEqual([])
  })
})

describe('dateFilter', () => {
  // dateFilter reads the clock itself: pin it to NOW, which the items are built from
  beforeEach(() => {
    vi.useFakeTimers({ now: NOW })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('offers the windows that exist, narrowest first, with older last', () => {
    const items = [{ at: ago(120 * DAY) }, { at: ago(3 * DAY) }]
    const [definition] = buildFilterDefinitions(items, [dateFilter<{ at: string }>(item => item.at)])
    expect(definition!.options.map(option => option.label)).toEqual(['Last 7 days', 'Last 30 days', 'Last 90 days', 'Older than 90 days'])
  })

  it('keeps the items inside the picked window', () => {
    const spec = dateFilter<{ at: string }>(item => item.at)
    const items = [{ at: ago(3 * DAY) }, { at: ago(120 * DAY) }]
    const state = { [spec.key]: { mode: 'include' as const, values: ['week'] } }
    expect(items.filter(item => matchesSpecs(item, [spec], state))).toEqual([items[0]])
  })

  it('gives two filters on the same list their own key', () => {
    expect(dateFilter(() => '', 'Created').key).not.toBe(dateFilter(() => '', 'Updated').key)
  })
})

describe('statusFilter', () => {
  it('lists statuses in the order a run goes through them, with a label', () => {
    const items = [{ s: 'failed' }, { s: 'pending' }, { s: 'completed' }, { s: 'failed' }]
    const [definition] = buildFilterDefinitions(items, [statusFilter<{ s: string }>(item => item.s)])
    expect(definition!.options.map(option => [option.label, option.count])).toEqual([['Pending', 1], ['Completed', 1], ['Failed', 2]])
  })

  it('still shows a status it does not know', () => {
    const [definition] = buildFilterDefinitions([{ s: 'weird' }], [statusFilter<{ s: string }>(item => item.s)])
    expect(definition!.options[0]!.label).toBe('weird')
  })
})

describe('runsFilter', () => {
  const spec = runsFilter<{ runs: number | null, of?: number }>(item => item.runs, item => item.of ?? 1)
  const label = (item: { runs: number | null, of?: number }) => {
    const [definition] = buildFilterDefinitions([item], [spec])
    return definition?.options[0]?.label
  }

  it('tells never run, run once and run again apart', () => {
    expect(label({ runs: 0 })).toBe('Never run')
    expect(label({ runs: 1 })).toBe('Run once')
    expect(label({ runs: 2 })).toBe('Run several times')
  })

  it('compares the executions of a batch to its experiments', () => {
    expect(label({ runs: 3, of: 3 })).toBe('Run once')
    expect(label({ runs: 4, of: 3 })).toBe('Run several times')
  })

  it('has nothing to say when the count is unknown', () => {
    expect(buildFilterDefinitions([{ runs: null }], [spec])).toEqual([])
  })

  it('lists the options in that order', () => {
    const [definition] = buildFilterDefinitions([{ runs: 2 }, { runs: 0 }, { runs: 1 }], [spec])
    expect(definition!.options.map(option => option.label)).toEqual(['Never run', 'Run once', 'Run several times'])
  })
})

describe('failuresFilter', () => {
  const spec = failuresFilter<{ failed: number | null }>(item => item.failed)

  it('separates executions with failed rows from clean ones', () => {
    const items = [{ failed: 3 }, { failed: 0 }, { failed: 0 }]
    const [definition] = buildFilterDefinitions(items, [spec])
    expect(definition!.options.map(option => [option.label, option.count])).toEqual([['With failed rows', 1], ['No failed rows', 2]])
  })

  it('does not call an experiment without execution clean', () => {
    expect(buildFilterDefinitions([{ failed: null }], [spec])).toEqual([])
  })

  it('keeps the items with failed rows', () => {
    const items = [{ failed: 3 }, { failed: 0 }]
    const state = { [spec.key]: { mode: 'include' as const, values: ['failed'] } }
    expect(items.filter(item => matchesSpecs(item, [spec], state))).toEqual([items[0]])
  })
})

describe('tagsFilter', () => {
  interface Item { tags: { id: number, name: string, color: 'red' | 'blue' }[] }
  const red = { id: 1, name: 'extraction', color: 'red' as const }
  const blue = { id: 2, name: 'paper', color: 'blue' as const }
  const items: Item[] = [{ tags: [red, blue] }, { tags: [blue] }, { tags: [] }]
  const spec = tagsFilter<Item>(item => item.tags)

  it('offers the tags that exist, with their colour and how many items carry them', () => {
    const [definition] = buildFilterDefinitions(items, [spec])
    expect(definition!.options.map(option => [option.label, option.count])).toEqual([['extraction', 1], ['paper', 2]])
    expect(definition!.options.every(option => option.dot?.startsWith('bg-'))).toBe(true)
  })

  it('keeps the items carrying any, or every, picked tag', () => {
    const pick = (mode: 'include' | 'all') => items.filter(item => matchesSpecs(item, [spec], { tags: { mode, values: ['extraction', 'paper'] } }))
    expect(pick('include')).toHaveLength(2)
    expect(pick('all')).toEqual([items[0]])
  })
})

describe('filterByTag', () => {
  it('filters on that tag alone, whatever was picked before', () => {
    const state = filterByTag({ tags: { mode: 'all', values: ['a', 'b'] }, status: { mode: 'include', values: ['failed'] } }, 'c')
    expect(state.tags).toEqual({ mode: 'include', values: ['c'] })
    expect(state.status).toEqual({ mode: 'include', values: ['failed'] })
  })

  it('lifts the filter when that tag is already the only one', () => {
    const once = filterByTag({}, 'a')
    expect(filterByTag(once, 'a').tags).toEqual({ mode: 'include', values: [] })
  })
})
