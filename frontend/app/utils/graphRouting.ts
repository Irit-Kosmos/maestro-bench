import type { GraphPoint, GraphRect } from './graphGeometry'
import { edgePath } from './graphGeometry'

// Routing of edges between nodes: every edge leaves the bottom of its source and enters the top of its
// target. Where several edges enter one node they take different spots along its top and different
// heights, so none hides another or shares its label's place. An edge that would cross a node on the
// way (an agent reading from one two rows up) goes around it instead.

export interface RouteLink { id: string, source: string, target: string }

export interface Route {
  d: string
  /** The arrowhead: two strokes meeting at the end of the edge */
  arrow: string
  /** Where the edge's pill sits */
  label: GraphPoint
  /** The corners of the path, before rounding. Empty for an edge that swings out and back */
  points: GraphPoint[]
}

// The arrowhead stops short of the node, like a pointer resting above it
export const ARROW_GAP = 5
const SPREAD = 36
const BUS_BASE = 34
const BUS_STEP = 22
const LANE_GAP = 26
const MARGIN = 12
const RADIUS = 14
const MIN_RUN = 56

const centerX = (r: GraphRect) => r.x + r.width / 2

/** Whether the axis-aligned segment a-b passes through `rect` grown by `margin` */
function hits(a: GraphPoint, b: GraphPoint, rect: GraphRect, margin = MARGIN): boolean {
  const left = rect.x - margin
  const right = rect.x + rect.width + margin
  const top = rect.y - margin
  const bottom = rect.y + rect.height + margin
  const x1 = Math.min(a.x, b.x)
  const x2 = Math.max(a.x, b.x)
  const y1 = Math.min(a.y, b.y)
  const y2 = Math.max(a.y, b.y)
  return x2 > left && x1 < right && y2 > top && y1 < bottom
}

function blocked(points: readonly GraphPoint[], obstacles: readonly GraphRect[]): boolean {
  for (let i = 1; i < points.length; i++) {
    if (obstacles.some(o => hits(points[i - 1]!, points[i]!, o)))
      return true
  }
  return false
}

/** A polyline with rounded corners: each corner is cut short by up to `radius`, never past half a segment */
function rounded(points: readonly GraphPoint[], radius = RADIUS): string {
  // Repeated points would give zero-length segments
  const pts = points.filter((p, i) => i === 0 || p.x !== points[i - 1]!.x || p.y !== points[i - 1]!.y)
  let d = `M${pts[0]!.x} ${pts[0]!.y}`
  for (let i = 1; i < pts.length - 1; i++) {
    const prev = pts[i - 1]!
    const corner = pts[i]!
    const next = pts[i + 1]!
    const before = Math.hypot(corner.x - prev.x, corner.y - prev.y)
    const after = Math.hypot(next.x - corner.x, next.y - corner.y)
    const r = Math.min(radius, before / 2, after / 2)
    const from = { x: corner.x + (prev.x - corner.x) * (r / before), y: corner.y + (prev.y - corner.y) * (r / before) }
    const to = { x: corner.x + (next.x - corner.x) * (r / after), y: corner.y + (next.y - corner.y) * (r / after) }
    d += `L${from.x} ${from.y}Q${corner.x} ${corner.y} ${to.x} ${to.y}`
  }
  const last = pts[pts.length - 1]!
  return `${d}L${last.x} ${last.y}`
}

const midpoint = (a: GraphPoint, b: GraphPoint): GraphPoint => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })

/** The pill goes on the horizontal run when there is room for it, else on the longest vertical one */
function labelOn(points: readonly GraphPoint[]): GraphPoint {
  const runs = points.slice(1).map((p, i) => ({ a: points[i]!, b: p }))
  // The last run long enough: the one just above the target, where the edge's own pill reads best
  const horizontal = runs.filter(r => r.a.y === r.b.y && Math.abs(r.b.x - r.a.x) >= MIN_RUN).at(-1)
  if (horizontal)
    return midpoint(horizontal.a, horizontal.b)
  const vertical = runs.filter(r => r.a.x === r.b.x).sort((p, q) => Math.abs(q.b.y - q.a.y) - Math.abs(p.b.y - p.a.y))[0]
  return vertical ? midpoint(vertical.a, vertical.b) : midpoint(points[0]!, points[points.length - 1]!)
}

function arrowAt(end: GraphPoint): string {
  return `M${end.x - 4.5} ${end.y - 5}L${end.x} ${end.y}L${end.x + 4.5} ${end.y - 5}`
}

/** `side`: which side of its target the edge enters on (-1 left, 1 right, 0 middle): a lane on that side crosses nothing */
function route(start: GraphPoint, end: GraphPoint, level: number, side: number, obstacles: readonly GraphRect[]): Route {
  const dy = end.y - start.y

  // The target is level with the source or above it: no room for runs, so it swings out and back
  if (dy < RADIUS * 2) {
    const { d, label } = edgePath(start, end)
    return { d, arrow: arrowAt(end), label, points: [] }
  }

  const busY = Math.min(Math.max(end.y - (BUS_BASE + level * BUS_STEP), start.y + 20), end.y - 12)
  const direct = Math.abs(end.x - start.x) < 0.5
    ? [start, end]
    : [start, { x: start.x, y: busY }, { x: end.x, y: busY }, end]

  let points = direct
  if (blocked(direct, obstacles)) {
    // Down the free lane beside the nodes in the way: off the source, along, down, then to the target
    const y1 = start.y + 18
    const bus = Math.max(busY, y1 + 12)
    const spanned = obstacles.filter(o => o.y + o.height > start.y && o.y < end.y)
    const cost = (lane: number) => Math.abs(lane - start.x) + Math.abs(lane - end.x) + (side * (lane - end.x) < 0 ? 1000 : 0)
    const lanes = spanned.flatMap(o => [o.x - LANE_GAP, o.x + o.width + LANE_GAP])
    const around = lanes
      .map(lane => ({
        lane,
        points: [start, { x: start.x, y: y1 }, { x: lane, y: y1 }, { x: lane, y: bus }, { x: end.x, y: bus }, end],
      }))
      .filter(c => !blocked(c.points, obstacles))
      .sort((p, q) => cost(p.lane) - cost(q.lane))[0]
    if (around)
      points = around.points
  }

  return { d: rounded(points), arrow: arrowAt(end), label: labelOn(points), points }
}

/**
 * Routes every edge. `shown` is where a node is drawn right now (edges follow it as it moves);
 * `settled` where it ends up, which the lanes are planned against so they do not flicker mid-motion.
 */
export function routeEdges(
  links: readonly RouteLink[],
  shown: (id: string) => GraphRect | undefined,
  settled: (id: string) => GraphRect | undefined,
  ids: readonly string[],
): Map<string, Route> {
  const routes = new Map<string, Route>()
  const valid = links.filter(l => shown(l.source) && shown(l.target))

  const incoming = new Map<string, RouteLink[]>()
  for (const link of valid)
    incoming.set(link.target, [...incoming.get(link.target) ?? [], link])

  for (const [targetId, list] of incoming) {
    const target = shown(targetId)!
    // Entry points follow the order of the sources, so edges do not cross on the way in
    const sorted = [...list].sort((a, b) => centerX(shown(a.source)!) - centerX(shown(b.source)!) || a.id.localeCompare(b.id))
    const spread = sorted.length > 1 ? Math.min(SPREAD, (target.width - 56) / (sorted.length - 1)) : 0
    const entries = sorted.map((link, i) => ({ link, x: centerX(target) + (i - (sorted.length - 1) / 2) * spread }))

    // Each side stacks its runs so that the entry nearest the centre runs highest: a run never cuts across another's drop
    const left = entries.filter(e => centerX(shown(e.link.source)!) < centerX(target) - 1)
    const right = entries.filter(e => centerX(shown(e.link.source)!) > centerX(target) + 1).reverse()
    const level = new Map<string, number>()
    left.forEach((e, i) => level.set(e.link.id, i))
    right.forEach((e, i) => level.set(e.link.id, i))

    for (const { link, x } of entries) {
      const from = shown(link.source)!
      const start = { x: centerX(from), y: from.y + from.height }
      const end = { x, y: target.y - ARROW_GAP }
      const obstacles = ids
        .filter(id => id !== link.source && id !== link.target)
        .flatMap((id) => {
          const rect = settled(id)
          return rect ? [rect] : []
        })
      routes.set(link.id, route(start, end, level.get(link.id) ?? 0, Math.sign(Math.round(x - centerX(target))), obstacles))
    }
  }
  return routes
}
