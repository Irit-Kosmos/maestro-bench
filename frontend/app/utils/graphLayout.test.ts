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

import { describe, expect, it } from 'vitest'
import { graphReaches, graphRows, layoutGraph } from './graphLayout'

const size = () => ({ width: 200, height: 100 })

describe('graphRows', () => {
  it('puts nodes under the lowest one they read from', () => {
    const rows = graphRows(['a', 'b', 'c', 'd'], [
      { source: 'a', target: 'b' },
      { source: 'b', target: 'c' },
      { source: 'a', target: 'c' },
    ])
    expect([...rows]).toEqual([['a', 0], ['b', 1], ['c', 2], ['d', 0]])
  })

  it('ignores edges to unknown nodes, loops and duplicates', () => {
    const rows = graphRows(['a', 'b'], [
      { source: 'a', target: 'a' },
      { source: 'x', target: 'b' },
      { source: 'a', target: 'b' },
      { source: 'a', target: 'b' },
    ])
    expect(rows.get('b')).toBe(1)
  })

  it('terminates on a cycle', () => {
    const rows = graphRows(['a', 'b', 'c'], [
      { source: 'a', target: 'b' },
      { source: 'b', target: 'c' },
      { source: 'c', target: 'a' },
    ])
    expect(rows.size).toBe(3)
    expect([...rows.values()].every(r => r >= 0 && r < 3)).toBe(true)
  })
})

describe('layoutGraph', () => {
  it('stacks a chain on one axis, rows apart', () => {
    const at = layoutGraph(['a', 'b', 'c'], [
      { source: 'a', target: 'b' },
      { source: 'b', target: 'c' },
    ], size, { gapY: 80 })
    expect(at.get('a')).toEqual({ x: -100, y: 0 })
    expect(at.get('b')).toEqual({ x: -100, y: 180 })
    expect(at.get('c')).toEqual({ x: -100, y: 360 })
  })

  it('centres a row of siblings under their source', () => {
    const at = layoutGraph(['a', 'b', 'c'], [
      { source: 'a', target: 'b' },
      { source: 'a', target: 'c' },
    ], size, { gapX: 40 })
    const b = at.get('b')!
    const c = at.get('c')!
    expect(b.y).toBe(c.y)
    expect(c.x - b.x).toBe(240)
    expect(b.x + c.x + 200).toBeCloseTo(0)
  })

  it('never overlaps two nodes of a row', () => {
    const ids = ['a', 'b', 'c', 'd', 'e']
    const at = layoutGraph(ids, [], size, { gapX: 24 })
    const xs = ids.map(id => at.get(id)!.x).sort((p, q) => p - q)
    xs.slice(1).forEach((x, i) => expect(x - xs[i]!).toBeGreaterThanOrEqual(224))
  })

  it('centres a short node on the row of a tall one', () => {
    const at = layoutGraph(['a', 'b'], [], id => id === 'a' ? { width: 200, height: 200 } : { width: 200, height: 100 })
    expect(at.get('a')!.y).toBe(0)
    expect(at.get('b')!.y).toBe(50)
  })

  it('orders siblings by where their source sits, to limit crossings', () => {
    // b reads from the left source, c from the right one: input order says c first
    const at = layoutGraph(['l', 'r', 'c', 'b'], [
      { source: 'l', target: 'b' },
      { source: 'r', target: 'c' },
    ], size)
    expect(at.get('b')!.x).toBeLessThan(at.get('c')!.x)
  })

  it('lays out nothing for an empty graph', () => {
    expect(layoutGraph([], [], size).size).toBe(0)
  })
})

describe('graphReaches', () => {
  const links = [
    { source: 'a', target: 'b' },
    { source: 'b', target: 'c' },
  ]

  it('follows edges in their direction only', () => {
    expect(graphReaches(links, 'a', 'c')).toBe(true)
    expect(graphReaches(links, 'c', 'a')).toBe(false)
  })

  it('reaches itself', () => {
    expect(graphReaches(links, 'a', 'a')).toBe(true)
  })
})
