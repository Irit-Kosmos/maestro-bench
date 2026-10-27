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

import type { GroupSpec } from './groups'
import { describe, expect, it } from 'vitest'
import { arrangeRows, GROUP_ROW } from './groups'

interface Run {
  id: number
  batch: number | null
  experiment: number
  status?: string
}

// Newest first, as the lists come
const runs: Run[] = [
  { id: 9, batch: 1, experiment: 10 },
  { id: 8, batch: null, experiment: 20 },
  { id: 7, batch: 1, experiment: 10 },
  { id: 6, batch: 1, experiment: 11 },
  { id: 5, batch: null, experiment: 21 },
  { id: 4, batch: null, experiment: 21 },
  { id: 3, batch: 2, experiment: 30 },
]

const spec: GroupSpec<Run> = {
  key: 'batch',
  label: 'Batch',
  icon: 'i-ph-arrows-split-bold',
  flow: true,
  value: run => run.batch,
  present: id => ({ label: `Batch ${id}`, icon: 'i-ph-arrows-split-bold' }),
  link: id => `/batches/${id}`,
  then: {
    key: 'experiment',
    value: run => run.experiment,
    minSize: 2,
  },
}

// Reads the layout as text: headers as "[level id (count)]", items as "id", with the trail as indentation
function outline(rows: ReturnType<typeof arrangeRows<Run>>['rows'], trails: ReturnType<typeof arrangeRows<Run>>['trails']) {
  return rows.map((row) => {
    const group = (row as any)[GROUP_ROW]
    if (group)
      return `${'  '.repeat(group.trail.length)}[${group.label} (${group.count})]`
    return `${'  '.repeat(trails.get((row as Run).id)?.length ?? 0)}${(row as Run).id}`
  })
}

describe('arrangeRows, flowing', () => {
  it('keeps the order of the list, a section sitting where its first item was', () => {
    const { rows, trails } = arrangeRows(runs, spec, 'id', new Set())
    expect(outline(rows, trails)).toEqual([
      '[Batch 1 (3)]',
      '  [10 (2)]',
      '    9',
      '    7',
      '  6',
      '8',
      '[21 (2)]',
      '  5',
      '  4',
      '[Batch 2 (1)]',
      '  3',
    ])
  })

  it('dissolves a section below its minimum into the level above', () => {
    const { rows } = arrangeRows(runs, spec, 'id', new Set())
    const headers = rows.map(row => (row as any)[GROUP_ROW]?.label).filter(Boolean)
    // Experiment 11 and 20 hold a single run each: no header. A batch of one keeps its header (its minimum is 1)
    expect(headers).not.toContain('11')
    expect(headers).not.toContain('20')
    expect(headers).toContain('Batch 2')
  })

  it('records the levels each item sits in, which the rails are drawn from', () => {
    const { trails } = arrangeRows(runs, spec, 'id', new Set())
    expect(trails.get(9)).toEqual(['batch', 'experiment'])
    expect(trails.get(6)).toEqual(['batch'])
    expect(trails.get(8)).toEqual([])
    expect(trails.get(5)).toEqual(['experiment'])
  })

  it('hides what is below a collapsed section, nested ones included', () => {
    const { rows, trails } = arrangeRows(runs, spec, 'id', new Set(['batch:1/']))
    expect(outline(rows, trails)).toEqual([
      '[Batch 1 (3)]',
      '8',
      '[21 (2)]',
      '  5',
      '  4',
      '[Batch 2 (1)]',
      '  3',
    ])
  })

  it('collapses a nested section on its own', () => {
    const { rows, trails } = arrangeRows(runs, spec, 'id', new Set(['batch:1/experiment:10/']))
    expect(outline(rows, trails).slice(0, 4)).toEqual(['[Batch 1 (3)]', '  [10 (2)]', '  6', '8'])
  })

  it('gives each header the keys of every row below it, collapsed or not', () => {
    const { rows } = arrangeRows(runs, spec, 'id', new Set(['batch:1/']))
    const batch = (rows[0] as any)[GROUP_ROW]
    expect(batch.keys).toEqual([9, 7, 6])
    expect(batch.collapsed).toBe(true)
    expect(batch.to).toBe('/batches/1')
    expect(batch.level).toBe('batch')
  })

  it('summarises what a section holds', () => {
    const withSummary: GroupSpec<Run> = {
      ...spec,
      summary: items => [{ label: `${items.filter(run => run.status === 'failed').length || ''}` }],
    }
    const { rows } = arrangeRows([{ id: 1, batch: 1, experiment: 1, status: 'failed' }, { id: 2, batch: 1, experiment: 2 }], withSummary, 'id', new Set())
    expect((rows[0] as any)[GROUP_ROW].summary).toEqual([{ label: '1' }])
  })

  it('drops the empty parts of a summary', () => {
    const withSummary: GroupSpec<Run> = { ...spec, summary: () => [{ label: '' }] }
    const { rows } = arrangeRows(runs, withSummary, 'id', new Set())
    expect((rows[0] as any)[GROUP_ROW].summary).toEqual([])
  })
})

describe('arrangeRows, sorted', () => {
  const sorted: GroupSpec<Run> = {
    key: 'batch',
    label: 'Batch',
    icon: 'i-ph-arrows-split-bold',
    value: run => run.batch,
    present: id => ({ label: `Batch ${id}` }),
    emptyLabel: 'No batch',
  }

  it('sorts the sections and sends the items without a value to the last one', () => {
    const { rows, trails } = arrangeRows(runs, sorted, 'id', new Set())
    expect(outline(rows, trails)).toEqual([
      '[Batch 1 (3)]',
      '9',
      '7',
      '6',
      '[Batch 2 (1)]',
      '3',
      '[No batch (3)]',
      '8',
      '5',
      '4',
    ])
    expect(trails.size).toBe(0)
  })
})
