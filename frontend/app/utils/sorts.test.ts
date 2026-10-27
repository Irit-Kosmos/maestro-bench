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

import type { SortSpec } from './sorts'
import { describe, expect, it } from 'vitest'
import { activeSortSpec, decodeSort, encodeSort, pickSort, sortItems } from './sorts'
import { dateSort, statusSort } from './sortSpecs'

interface Run {
  id: number
  name: string | null
  cost: number | null
}

const runs: Run[] = [
  { id: 1, name: 'Run 10', cost: 0.5 },
  { id: 2, name: null, cost: 2 },
  { id: 3, name: 'run 2', cost: null },
  { id: 4, name: 'Alpha', cost: 0.5 },
]

const byName: SortSpec<Run> = { key: 'name', label: 'Name', icon: 'i-ph-text-aa-bold', value: run => run.name }
const byCost: SortSpec<Run> = { key: 'cost', label: 'Cost', icon: 'i-ph-coins-bold', defaultDirection: 'desc', value: run => run.cost }

const ids = (list: Run[]) => list.map(run => run.id)

describe('sortItems', () => {
  it('sorts text without minding case, and numbers inside it by value', () => {
    expect(ids(sortItems(runs, byName, 'asc'))).toEqual([4, 3, 1, 2])
  })

  it('reverses the order when descending', () => {
    expect(ids(sortItems(runs, byName, 'desc'))).toEqual([1, 3, 4, 2])
  })

  it('keeps the items without a value last, whichever way it goes', () => {
    expect(ids(sortItems(runs, byCost, 'asc'))).toEqual([1, 4, 2, 3])
    expect(ids(sortItems(runs, byCost, 'desc'))).toEqual([2, 1, 4, 3])
  })

  it('keeps items that read equal in the order they came', () => {
    expect(ids(sortItems(runs, byCost, 'asc')).slice(0, 2)).toEqual([1, 4])
    expect(ids(sortItems(runs, byCost, 'desc')).slice(1, 3)).toEqual([1, 4])
  })

  it('leaves the list it was given alone', () => {
    const before = ids(runs)
    sortItems(runs, byName, 'asc')
    expect(ids(runs)).toEqual(before)
  })

  it('treats NaN as no value', () => {
    const spec: SortSpec<Run> = { ...byCost, value: run => run.id === 1 ? Number.NaN : run.cost }
    expect(ids(sortItems(runs, spec, 'asc'))).toEqual([4, 2, 1, 3])
  })
})

describe('shared sorts', () => {
  it('reads dates as time, the latest first by default', () => {
    const spec = dateSort<{ at: string | null }>(item => item.at)
    expect(spec.defaultDirection).toBe('desc')
    const items = [{ at: '2026-01-02T00:00:00Z' }, { at: null }, { at: '2026-03-01T00:00:00Z' }]
    expect(sortItems(items, spec, 'desc').map(item => item.at)).toEqual(['2026-03-01T00:00:00Z', '2026-01-02T00:00:00Z', null])
  })

  it('reads statuses in the order a run goes through them, an unknown one last', () => {
    const spec = statusSort<{ status: string }>(item => item.status)
    const items = [{ status: 'failed' }, { status: 'weird' }, { status: 'pending' }, { status: 'completed' }]
    expect(sortItems(items, spec, 'asc').map(item => item.status)).toEqual(['pending', 'completed', 'failed', 'weird'])
  })
})

describe('pickSort', () => {
  it('starts in the direction the entry prefers', () => {
    expect(pickSort(byName, null)).toEqual({ key: 'name', direction: 'asc' })
    expect(pickSort(byCost, { key: 'name', direction: 'asc' })).toEqual({ key: 'cost', direction: 'desc' })
  })

  it('keeps the direction when the entry in use is picked again', () => {
    expect(pickSort(byCost, { key: 'cost', direction: 'asc' })).toEqual({ key: 'cost', direction: 'asc' })
  })
})

describe('activeSortSpec', () => {
  it('finds the entry a state names, and nothing for a stale one', () => {
    expect(activeSortSpec([byName, byCost], { key: 'cost', direction: 'asc' })).toBe(byCost)
    expect(activeSortSpec([byName], { key: 'cost', direction: 'asc' })).toBeNull()
    expect(activeSortSpec([byName], null)).toBeNull()
  })
})

describe('encodeSort / decodeSort', () => {
  it('round-trips a sort, keys with a colon included', () => {
    for (const state of [{ key: 'cost', direction: 'desc' as const }, { key: 'date-created:at', direction: 'asc' as const }])
      expect(decodeSort(encodeSort(state))).toEqual(state)
  })

  it('reads anything else as no sort', () => {
    expect(decodeSort(encodeSort(null))).toBeNull()
    for (const stored of [undefined, null, '', 'none', ':asc', 'cost:sideways', 'cost'])
      expect(decodeSort(stored)).toBeNull()
  })
})
