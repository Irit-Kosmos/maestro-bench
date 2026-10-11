// Geometry of the graph canvas: viewport maths, edge paths and the spring that moves nodes.
// Pure functions only, so they can be tested without a browser.

export interface GraphPoint { x: number, y: number }
export interface GraphSize { width: number, height: number }
export interface GraphRect extends GraphPoint, GraphSize {}

/** Where the world sits in the canvas: `x`/`y` is its translation in screen pixels, `k` its scale */
export interface GraphViewport { x: number, y: number, k: number }

/** The part of the canvas that shows the graph: `insets` is what overlays cover (a side panel, say) */
export interface GraphArea extends GraphSize {
  insets?: { top?: number, right?: number, bottom?: number, left?: number }
}

export const GRAPH_MIN_ZOOM = 0.3
export const GRAPH_MAX_ZOOM = 2

export function clampZoom(k: number): number {
  return Math.min(GRAPH_MAX_ZOOM, Math.max(GRAPH_MIN_ZOOM, k))
}

/** Zooms to `k` around a screen point: the world point under it does not move */
export function zoomAt(view: GraphViewport, k: number, anchor: GraphPoint): GraphViewport {
  const next = clampZoom(k)
  const ratio = next / view.k
  return {
    x: anchor.x - (anchor.x - view.x) * ratio,
    y: anchor.y - (anchor.y - view.y) * ratio,
    k: next,
  }
}

export function boundsOf(rects: readonly GraphRect[]): GraphRect | null {
  if (rects.length === 0)
    return null
  const left = Math.min(...rects.map(r => r.x))
  const top = Math.min(...rects.map(r => r.y))
  const right = Math.max(...rects.map(r => r.x + r.width))
  const bottom = Math.max(...rects.map(r => r.y + r.height))
  return { x: left, y: top, width: right - left, height: bottom - top }
}

function visibleArea(area: GraphArea) {
  const { top = 0, right = 0, bottom = 0, left = 0 } = area.insets ?? {}
  return { top, left, width: Math.max(1, area.width - left - right), height: Math.max(1, area.height - top - bottom) }
}

/** The viewport that shows `bounds` whole and centred in the visible area, never zoomed in past `maxZoom` */
export function fitViewport(bounds: GraphRect, area: GraphArea, { padding = 48, maxZoom = 1 } = {}): GraphViewport {
  const visible = visibleArea(area)
  const k = Math.min(
    maxZoom,
    clampZoom(Math.min((visible.width - padding * 2) / bounds.width, (visible.height - padding * 2) / bounds.height)),
  )
  return {
    k,
    x: visible.left + visible.width / 2 - (bounds.x + bounds.width / 2) * k,
    y: visible.top + visible.height / 2 - (bounds.y + bounds.height / 2) * k,
  }
}

/** The smallest pan that brings `rect` fully into the visible area. The same viewport when it already is */
export function revealViewport(view: GraphViewport, rect: GraphRect, area: GraphArea, padding = 32): GraphViewport {
  const visible = visibleArea(area)
  const shift = (start: number, size: number, from: number, length: number) => {
    const lo = from + padding
    const hi = from + length - padding
    if (size > hi - lo || start < lo)
      return lo - start
    return start + size > hi ? hi - (start + size) : 0
  }
  const dx = shift(rect.x * view.k + view.x, rect.width * view.k, visible.left, visible.width)
  const dy = shift(rect.y * view.k + view.y, rect.height * view.k, visible.top, visible.height)
  return dx === 0 && dy === 0 ? view : { ...view, x: view.x + dx, y: view.y + dy }
}

/**
 * Path of an edge leaving `from` downwards and entering `to` from above: a vertical run, a horizontal
 * run half-way, a vertical run, with rounded corners. Edges leaving one node share their first run and
 * split like a tree. `label` is where its pill sits: on the last run, so that edges ending in
 * different nodes never stack their pills.
 */
export function edgePath(from: GraphPoint, to: GraphPoint, radius = 14): { d: string, label: GraphPoint } {
  const dx = to.x - from.x
  const dy = to.y - from.y

  if (Math.abs(dx) < 0.5 && dy >= 0)
    return { d: `M${from.x} ${from.y}V${to.y}`, label: { x: from.x, y: from.y + dy / 2 } }

  // Target level with the source or above it (a node dragged under its own input): no room for
  // a step, so the edge swings out and back
  if (dy < radius * 2) {
    const reach = Math.max(60, Math.abs(dy) / 2 + 40)
    // Aligned ends would make the curve a straight line back through the nodes: bow it out to the side
    const bow = Math.abs(dx) < 40 ? 110 : 0
    return {
      d: `M${from.x} ${from.y}C${from.x + bow} ${from.y + reach} ${to.x + bow} ${to.y - reach} ${to.x} ${to.y}`,
      label: { x: (from.x + to.x) / 2 + bow * 0.75, y: (from.y + to.y) / 2 },
    }
  }

  const midY = from.y + dy / 2
  const side = Math.sign(dx)
  const r = Math.min(radius, Math.abs(dx) / 2, dy / 4)
  return {
    d: [
      `M${from.x} ${from.y}`,
      `V${midY - r}`,
      `Q${from.x} ${midY} ${from.x + side * r} ${midY}`,
      `H${to.x - side * r}`,
      `Q${to.x} ${midY} ${to.x} ${midY + r}`,
      `V${to.y}`,
    ].join(''),
    label: { x: to.x, y: midY + (to.y - midY) / 2 },
  }
}

export interface SpringState { x: number, v: number }

/**
 * Moves `state` towards `target` as a critically damped spring: it never overshoots, and since it
 * keeps its velocity, retargeting mid-flight bends the motion instead of restarting it.
 * Closed-form, so the result does not depend on the frame rate.
 */
export function springStep(state: SpringState, target: number, dt: number, omega = 22): void {
  const offset = state.x - target
  const c2 = state.v + omega * offset
  const decay = Math.exp(-omega * dt)
  state.x = target + (offset + c2 * dt) * decay
  state.v = (c2 - omega * (offset + c2 * dt)) * decay
}

export function springSettled(state: SpringState, target: number): boolean {
  return Math.abs(state.x - target) < 0.1 && Math.abs(state.v) < 1
}
