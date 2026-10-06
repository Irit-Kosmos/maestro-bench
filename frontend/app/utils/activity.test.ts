import type { StudyActivityEvent } from '~/types'
import { describe, expect, it } from 'vitest'
import { describeRun, groupActivity } from './activity'

const alice = { id: 1, display_name: 'Alice', avatar_url: null }
const bob = { id: 2, display_name: 'Bob', avatar_url: null }

let counter = 0
function event(type: StudyActivityEvent['type'], at: string, extra: Partial<StudyActivityEvent> = {}): StudyActivityEvent {
  counter += 1
  return {
    type,
    at,
    actor: type === 'item_added' ? alice : null,
    item: { kind: 'experiment', item_id: counter, name: `Run ${counter}` },
    note: null,
    ...extra,
  }
}

const added = (at: string, actor = alice) => event('item_added', at, { actor })
const done = (at: string) => event('experiment_completed', at)

describe('groupActivity', () => {
  it('folds a run of lines added together by one person', () => {
    const rows = groupActivity([
      added('2026-10-06T20:03:00Z'),
      added('2026-10-06T20:02:00Z'),
      added('2026-10-06T20:01:00Z'),
    ])

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({ kind: 'group', type: 'item_added', actor: alice })
    expect(rows[0]!.kind === 'group' && rows[0]!.events).toHaveLength(3)
  })

  it('leaves short runs as they are', () => {
    const rows = groupActivity([added('2026-10-06T20:02:00Z'), added('2026-10-06T20:01:00Z')])

    expect(rows.map(row => row.kind)).toEqual(['event', 'event'])
  })

  it('does not fold what different people added together, nor what is far apart in time', () => {
    const byOthers = groupActivity([
      added('2026-10-06T20:03:00Z'),
      added('2026-10-06T20:02:00Z', bob),
      added('2026-10-06T20:01:00Z'),
    ])
    const apart = groupActivity([
      added('2026-10-06T20:03:00Z'),
      added('2026-10-06T20:02:00Z'),
      added('2026-10-06T10:00:00Z'),
    ])

    expect(byOthers.every(row => row.kind === 'event')).toBe(true)
    expect(apart.map(row => row.kind)).toEqual(['event', 'event', 'event'])
  })

  it('folds completions a day apart at most, and starts a new fold after a longer wait', () => {
    const rows = groupActivity([
      done('2026-10-06T10:00:00Z'),
      done('2026-10-06T08:00:00Z'),
      done('2026-10-05T20:00:00Z'),
      done('2026-09-30T10:00:00Z'),
      done('2026-09-30T09:00:00Z'),
      done('2026-09-30T08:00:00Z'),
    ])

    expect(rows.map(row => row.kind)).toEqual(['group', 'group'])
    expect(rows.map(row => row.kind === 'group' ? row.events.length : 0)).toEqual([3, 3])
  })

  it('never folds notes, and a note ends the run', () => {
    const note = event('note', '2026-10-06T20:02:30Z', { item: { kind: 'study', item_id: 1, name: 'S' } })
    const rows = groupActivity([
      added('2026-10-06T20:04:00Z'),
      added('2026-10-06T20:03:00Z'),
      note,
      added('2026-10-06T20:02:00Z'),
      added('2026-10-06T20:01:00Z'),
    ])

    expect(rows.map(row => row.kind)).toEqual(['event', 'event', 'event', 'event', 'event'])
  })

  it('keeps the key of a fold when a newer line joins it', () => {
    const older = [added('2026-10-06T20:02:00Z'), added('2026-10-06T20:01:00Z'), added('2026-10-06T20:00:00Z')]
    const [before] = groupActivity(older)
    const [after] = groupActivity([added('2026-10-06T20:03:00Z'), ...older])

    expect(before).toMatchObject({ kind: 'group' })
    expect(after).toMatchObject({ kind: 'group', key: (before as { key: string }).key })
  })
})

describe('describeRun', () => {
  it('counts what is in the run by kind', () => {
    const batch = event('item_added', '2026-10-06T20:00:00Z', { item: { kind: 'batch', item_id: 1, name: 'B' } })

    expect(describeRun([added('2026-10-06T20:01:00Z'), added('2026-10-06T20:02:00Z'), batch])).toBe('2 experiments and 1 batch')
    expect(describeRun([batch])).toBe('1 batch')
    expect(describeRun([])).toBe('')
  })
})
