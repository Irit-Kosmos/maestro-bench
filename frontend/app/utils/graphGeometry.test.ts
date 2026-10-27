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
import { boundsOf, edgePath, fitViewport, GRAPH_MAX_ZOOM, GRAPH_MIN_ZOOM, revealViewport, springSettled, springStep, zoomAt } from './graphGeometry'

describe('zoomAt', () => {
  it('keeps the world point under the anchor in place', () => {
    const view = { x: 40, y: -20, k: 1 }
    const anchor = { x: 300, y: 200 }
    const next = zoomAt(view, 1.5, anchor)
    // world point under the anchor: (screen - translation) / scale
    expect((anchor.x - view.x) / view.k).toBeCloseTo((anchor.x - next.x) / next.k)
    expect((anchor.y - view.y) / view.k).toBeCloseTo((anchor.y - next.y) / next.k)
  })

  it('stays within the zoom limits', () => {
    expect(zoomAt({ x: 0, y: 0, k: 1 }, 50, { x: 0, y: 0 }).k).toBe(GRAPH_MAX_ZOOM)
    expect(zoomAt({ x: 0, y: 0, k: 1 }, 0.001, { x: 0, y: 0 }).k).toBe(GRAPH_MIN_ZOOM)
  })
})

describe('boundsOf', () => {
  it('has nothing to bound without rects', () => {
    expect(boundsOf([])).toBeNull()
  })

  it('wraps every rect', () => {
    expect(boundsOf([
      { x: -100, y: 0, width: 200, height: 50 },
      { x: 20, y: 120, width: 80, height: 40 },
    ])).toEqual({ x: -100, y: 0, width: 200, height: 160 })
  })
})

describe('fitViewport', () => {
  const bounds = { x: -150, y: 0, width: 300, height: 200 }

  it('centres a small graph without zooming in on it', () => {
    const view = fitViewport(bounds, { width: 1000, height: 600 })
    expect(view.k).toBe(1)
    expect(view.x).toBeCloseTo(500)
    expect(view.y).toBeCloseTo(200)
  })

  it('shrinks a graph that does not fit', () => {
    const view = fitViewport({ x: 0, y: 0, width: 1200, height: 800 }, { width: 600, height: 400 })
    expect(view.k).toBeLessThan(0.5)
    expect(1200 * view.k).toBeLessThanOrEqual(600)
    expect(800 * view.k).toBeLessThanOrEqual(400)
  })

  it('centres in what an overlay leaves visible', () => {
    const view = fitViewport(bounds, { width: 1000, height: 600, insets: { right: 400 } })
    expect(view.x).toBeCloseTo(300)
  })
})

describe('revealViewport', () => {
  const area = { width: 1000, height: 600 }

  it('leaves the viewport alone when the rect is visible', () => {
    const view = { x: 0, y: 0, k: 1 }
    expect(revealViewport(view, { x: 100, y: 100, width: 200, height: 100 }, area)).toBe(view)
  })

  it('pans the least that brings the rect in', () => {
    const view = { x: 0, y: 0, k: 1 }
    const next = revealViewport(view, { x: 900, y: 100, width: 200, height: 100 }, area, 20)
    expect(next.x).toBe(-120)
    expect(next.y).toBe(0)
    expect(next.k).toBe(1)
  })

  it('does not hide the rect behind an overlay', () => {
    const next = revealViewport({ x: 0, y: 0, k: 1 }, { x: 500, y: 100, width: 200, height: 100 }, { ...area, insets: { right: 400 } }, 20)
    expect(500 + next.x + 200).toBeLessThanOrEqual(600 - 20)
  })
})

describe('edgePath', () => {
  it('goes straight down when the ends are aligned', () => {
    const { d, label } = edgePath({ x: 0, y: 100 }, { x: 0, y: 200 })
    expect(d).toBe('M0 100V200')
    expect(label).toEqual({ x: 0, y: 150 })
  })

  it('steps sideways half-way down, towards the target', () => {
    const { d, label } = edgePath({ x: 0, y: 0 }, { x: 100, y: 100 })
    expect(d.startsWith('M0 0V')).toBe(true)
    expect(d).toContain('H')
    expect(d.endsWith('V100')).toBe(true)
    // pill on the last run, under the half-way line
    expect(label.x).toBe(100)
    expect(label.y).toBeGreaterThan(50)
    expect(label.y).toBeLessThan(100)
  })

  it('mirrors for a target on the left', () => {
    const left = edgePath({ x: 0, y: 0 }, { x: -100, y: 100 })
    const right = edgePath({ x: 0, y: 0 }, { x: 100, y: 100 })
    expect(left.label.x).toBe(-100)
    expect(left.label.y).toBe(right.label.y)
  })

  it('keeps its corners inside a tight step', () => {
    // 4px sideways, 40px down: the radius must shrink to fit
    const { d } = edgePath({ x: 0, y: 0 }, { x: 4, y: 40 })
    const numbers = d.match(/-?\d+(\.\d+)?/g)!.map(Number)
    expect(numbers.every(n => Number.isFinite(n))).toBe(true)
  })

  it('swings out and back when the target is not below the source', () => {
    const { d } = edgePath({ x: 0, y: 200 }, { x: 80, y: 100 })
    expect(d).toContain('C')
  })
})

describe('springStep', () => {
  it('settles on its target without overshooting', () => {
    const state = { x: 0, v: 0 }
    let max = 0
    for (let i = 0; i < 120 && !springSettled(state, 100); i++) {
      springStep(state, 100, 1 / 60)
      max = Math.max(max, state.x)
    }
    expect(springSettled(state, 100)).toBe(true)
    expect(max).toBeLessThanOrEqual(100)
  })

  it('does not depend on the frame rate', () => {
    const fast = { x: 0, v: 0 }
    const slow = { x: 0, v: 0 }
    for (let i = 0; i < 12; i++)
      springStep(fast, 100, 1 / 120)
    for (let i = 0; i < 6; i++)
      springStep(slow, 100, 1 / 60)
    expect(fast.x).toBeCloseTo(slow.x, 6)
  })

  it('keeps its velocity when the target moves', () => {
    const state = { x: 0, v: 0 }
    for (let i = 0; i < 6; i++)
      springStep(state, 100, 1 / 60)
    const velocity = state.v
    expect(velocity).toBeGreaterThan(0)
    springStep(state, 0, 1 / 600)
    // still heading the same way for a moment, rather than reversing at once
    expect(state.v).toBeGreaterThan(0)
  })
})
