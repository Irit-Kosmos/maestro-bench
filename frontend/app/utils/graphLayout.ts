import type { GraphPoint, GraphSize } from './graphGeometry'

// Layered layout, top to bottom: an agent sits one row under the lowest agent it reads from,
// and agents that do not depend on each other share a row.

export interface GraphLink { source: string, target: string }

/** An edge as the canvas draws it */
export interface GraphEdge extends GraphLink {
  id: string
  /** Pill on the edge, e.g. the variables it carries */
  label?: string
  /** What the edge connects, for assistive technology: "A to B" */
  name?: string
  /** Whether the canvas offers to remove it. Defaults to yes */
  deletable?: boolean
  /** What removing it does, for its button: "Run in parallel" rather than "Remove connection" */
  removeLabel?: string
}

interface LayoutOptions {
  /** Space between two nodes of a row */
  gapX?: number
  /** Space between two rows: edges, their labels and the add button live there */
  gapY?: number
}

function validLinks(ids: ReadonlySet<string>, links: readonly GraphLink[]): GraphLink[] {
  const seen = new Set<string>()
  return links.filter((link) => {
    const key = `${link.source}>${link.target}`
    if (link.source === link.target || !ids.has(link.source) || !ids.has(link.target) || seen.has(key))
      return false
    seen.add(key)
    return true
  })
}

/** Row of each node: 0 without incoming edge, else one past its lowest source. Bounded, so a cycle cannot hang it */
export function graphRows(ids: readonly string[], links: readonly GraphLink[]): Map<string, number> {
  const valid = validLinks(new Set(ids), links)
  const row = new Map(ids.map(id => [id, 0]))
  for (let pass = 0; pass < ids.length; pass++) {
    let changed = false
    for (const { source, target } of valid) {
      const next = row.get(source)! + 1
      if (row.get(target)! < next && next < ids.length) {
        row.set(target, next)
        changed = true
      }
    }
    if (!changed)
      break
  }
  return row
}

/** Top-left of every node, each row centred on x = 0 and the first row at y = 0 */
export function layoutGraph(
  ids: readonly string[],
  links: readonly GraphLink[],
  sizeOf: (id: string) => GraphSize,
  { gapX = 48, gapY = 96 }: LayoutOptions = {},
): Map<string, GraphPoint> {
  const valid = validLinks(new Set(ids), links)
  const rowOf = graphRows(ids, valid)

  const rows: string[][] = []
  for (const id of ids)
    (rows[rowOf.get(id)!] ??= []).push(id)

  // Nodes lean towards the average position of what they read from, so edges cross less
  const order = new Map<string, number>()
  rows.forEach(row => row.forEach((id, i) => order.set(id, i)))
  for (let row = 1; row < rows.length; row++) {
    const weight = (id: string) => {
      const sources = valid.filter(l => l.target === id && rowOf.get(l.source) === row - 1)
      return sources.length ? sources.reduce((sum, l) => sum + order.get(l.source)!, 0) / sources.length : order.get(id)!
    }
    rows[row]!.sort((a, b) => weight(a) - weight(b) || order.get(a)! - order.get(b)!)
    rows[row]!.forEach((id, i) => order.set(id, i))
  }

  const positions = new Map<string, GraphPoint>()
  let y = 0
  for (const row of rows) {
    if (!row?.length)
      continue
    const sizes = row.map(sizeOf)
    const width = sizes.reduce((sum, s) => sum + s.width, 0) + gapX * (row.length - 1)
    const height = Math.max(...sizes.map(s => s.height))
    let x = -width / 2
    row.forEach((id, i) => {
      positions.set(id, { x, y: y + (height - sizes[i]!.height) / 2 })
      x += sizes[i]!.width + gapX
    })
    y += height + gapY
  }
  return positions
}

/** Whether `to` can be reached from `from` by following the edges: connecting `to` back to `from` would close a cycle */
export function graphReaches(links: readonly GraphLink[], from: string, to: string): boolean {
  const seen = new Set<string>([from])
  const queue = [from]
  while (queue.length > 0) {
    const current = queue.shift()!
    if (current === to)
      return true
    for (const link of links) {
      if (link.source === current && !seen.has(link.target)) {
        seen.add(link.target)
        queue.push(link.target)
      }
    }
  }
  return false
}
