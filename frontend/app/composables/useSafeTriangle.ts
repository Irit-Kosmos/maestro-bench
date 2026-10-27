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

import type { Ref } from 'vue'

interface Point { x: number, y: number }

const HOLD_MS = 150

function inTriangle(p: Point, a: Point, b: Point, c: Point) {
  const side = (u: Point, v: Point) => (p.x - v.x) * (u.y - v.y) - (u.x - v.x) * (p.y - v.y)
  const d1 = side(a, b)
  const d2 = side(b, c)
  const d3 = side(c, a)
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0))
}

/**
 * Keeps a master/detail picker steady while the pointer travels from a row to the panel beside it.
 * Rows sit in `listEl` and the panel to its right; `containerEl` wraps both and gives the panel's height.
 * While the pointer stays inside the triangle between where it left the active row and the panel's
 * near corners, hovering other rows is held back (at most `HOLD_MS`); leaving the triangle, clicking
 * or focusing a row switches at once. `active` is the key of the row whose panel is shown.
 */
export function useSafeTriangle(active: Ref<string | undefined>) {
  const containerEl = ref<HTMLElement>()
  const listEl = ref<HTMLElement>()

  let anchor: Point | undefined
  let pendingKey: string | undefined
  let timer: ReturnType<typeof setTimeout> | undefined

  function isHeadingToPanel(p: Point) {
    if (!anchor || !containerEl.value || !listEl.value)
      return false
    const { top, bottom } = containerEl.value.getBoundingClientRect()
    const edge = listEl.value.getBoundingClientRect().right
    return inTriangle(p, anchor, { x: edge, y: top }, { x: edge, y: bottom })
  }

  function cancel() {
    clearTimeout(timer)
    pendingKey = undefined
  }

  function select(key: string) {
    cancel()
    active.value = key
  }

  function hold() {
    clearTimeout(timer)
    timer = setTimeout(() => pendingKey && select(pendingKey), HOLD_MS)
  }

  function onEnter(key: string, event: PointerEvent) {
    if (key === active.value)
      return cancel()
    if (event.pointerType !== 'touch' && isHeadingToPanel({ x: event.clientX, y: event.clientY })) {
      pendingKey = key
      hold()
    }
    else {
      select(key)
    }
  }

  function onMove(event: PointerEvent) {
    const point = { x: event.clientX, y: event.clientY }
    if (!pendingKey)
      anchor = point
    else if (isHeadingToPanel(point))
      hold()
    else
      select(pendingKey)
  }

  onScopeDispose(cancel)

  return { containerEl, listEl, select, onEnter, onMove, onLeave: cancel }
}
