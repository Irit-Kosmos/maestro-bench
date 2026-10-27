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

import type { GraphRect } from './graphGeometry'
import { describe, expect, it } from 'vitest'
import { routeEdges } from './graphRouting'

const W = 264
const H = 140
// A column of three nodes, a gap of 100 between rows
const column: Record<string, GraphRect> = {
  a: { x: -W / 2, y: 0, width: W, height: H },
  b: { x: -W / 2, y: 240, width: W, height: H },
  c: { x: -W / 2, y: 480, width: W, height: H },
}
function run(links: { id: string, source: string, target: string }[], rects: Record<string, GraphRect> = column) {
  return routeEdges(links, id => rects[id], id => rects[id], Object.keys(rects))
}

describe('routeEdges', () => {
  it('draws a chain straight down', () => {
    const routes = run([{ id: 'ab', source: 'a', target: 'b' }])
    const { points } = routes.get('ab')!
    expect(points).toHaveLength(2)
    expect(points[0]!.x).toBe(points[1]!.x)
    // pill half-way along
    expect(routes.get('ab')!.label.y).toBeCloseTo((H + 240 - 5) / 2)
  })

  it('goes around a node standing in the way, on the side nearest the ends', () => {
    // a feeds c, and b sits between them in the same column
    const { points } = run([{ id: 'ac', source: 'a', target: 'c' }]).get('ac')!
    const lane = points.find((p, i) => i > 0 && p.x !== points[0]!.x)!.x
    expect(Math.abs(lane)).toBeGreaterThan(W / 2)
    // no run of the path goes through b
    for (let i = 1; i < points.length; i++) {
      const [p, q] = [points[i - 1]!, points[i]!]
      const crosses = Math.max(p.x, q.x) > column.b!.x && Math.min(p.x, q.x) < column.b!.x + W
        && Math.max(p.y, q.y) > column.b!.y && Math.min(p.y, q.y) < column.b!.y + H
      expect(crosses).toBe(false)
    }
  })

  it('keeps both edges of an agent reading two others, each in its own place', () => {
    const routes = run([
      { id: 'ac', source: 'a', target: 'c' },
      { id: 'bc', source: 'b', target: 'c' },
    ])
    const ac = routes.get('ac')!
    const bc = routes.get('bc')!
    const entry = (r: typeof ac) => r.points[r.points.length - 1]!
    // they enter c at different spots, symmetric about its centre
    expect(entry(ac).x).not.toBe(entry(bc).x)
    expect(entry(ac).x + entry(bc).x).toBeCloseTo(0)
    // and their pills do not sit on top of each other
    expect(Math.hypot(ac.label.x - bc.label.x, ac.label.y - bc.label.y)).toBeGreaterThan(24)
  })

  it('takes the lane on the side its entry is on, so that two edges into one node do not cross', () => {
    const routes = run([
      { id: 'ac', source: 'a', target: 'c' },
      { id: 'bc', source: 'b', target: 'c' },
    ])
    const ac = routes.get('ac')!
    const entry = ac.points.at(-1)!.x
    const lane = ac.points.find((p, i) => i > 0 && p.x !== ac.points[0]!.x)!.x
    // the left entry (a sorts before b) is reached from the left
    expect(entry).toBeLessThan(0)
    expect(lane).toBeLessThan(entry)
  })

  it('puts the pill of a lane edge above its target, not under its source', () => {
    const { label } = run([{ id: 'ac', source: 'a', target: 'c' }]).get('ac')!
    expect(label.y).toBeGreaterThan(column.b!.y + H)
  })

  it('enters a node left to right in the order of its sources', () => {
    const rects: Record<string, GraphRect> = {
      l: { x: -400, y: 0, width: W, height: H },
      r: { x: 140, y: 0, width: W, height: H },
      t: { x: -W / 2, y: 300, width: W, height: H },
    }
    const routes = run([
      { id: 'rt', source: 'r', target: 't' },
      { id: 'lt', source: 'l', target: 't' },
    ], rects)
    const x = (id: string) => routes.get(id)!.points.at(-1)!.x
    expect(x('lt')).toBeLessThan(x('rt'))
  })

  it('spreads many entries inside the width of the node', () => {
    const rects: Record<string, GraphRect> = { t: { x: 0, y: 400, width: W, height: H } }
    const links = ['a', 'b', 'c', 'd', 'e', 'f'].map((id, i) => {
      rects[id] = { x: i * 300, y: 0, width: W, height: H }
      return { id: `${id}t`, source: id, target: 't' }
    })
    const xs = [...run(links, rects).values()].map(r => r.points.at(-1)!.x)
    expect(Math.min(...xs)).toBeGreaterThan(0)
    expect(Math.max(...xs)).toBeLessThan(W)
  })

  it('leaves out an edge whose end is not on the graph', () => {
    expect(run([{ id: 'ax', source: 'a', target: 'x' }]).size).toBe(0)
  })

  it('swings out and back when the target is above its source', () => {
    const routes = run([{ id: 'ca', source: 'c', target: 'a' }])
    expect(routes.get('ca')!.points).toEqual([])
    expect(routes.get('ca')!.d).toContain('C')
  })

  it('rounds corners without leaving the lanes', () => {
    const { d } = run([{ id: 'ac', source: 'a', target: 'c' }]).get('ac')!
    expect(d.startsWith('M')).toBe(true)
    expect(d).toContain('Q')
    expect(d.match(/-?\d+(\.\d+)?/g)!.every(n => Number.isFinite(Number(n)))).toBe(true)
  })
})
