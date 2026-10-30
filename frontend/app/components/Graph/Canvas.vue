<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts" generic="N extends { id: string }">
import type { GraphArea, GraphPoint, GraphRect, GraphSize, GraphViewport, SpringState } from '~/utils/graphGeometry'
import type { GraphEdge } from '~/utils/graphLayout'
import { useEventListener, usePreferredReducedMotion } from '@vueuse/core'
import { boundsOf, edgePath, fitViewport, GRAPH_MAX_ZOOM, GRAPH_MIN_ZOOM, revealViewport, springSettled, springStep, zoomAt } from '~/utils/graphGeometry'
import { layoutGraph } from '~/utils/graphLayout'
import { ARROW_GAP, routeEdges } from '~/utils/graphRouting'

// Our own node canvas. Nodes are placed by layoutGraph (rows, top to bottom) rather than by hand, so
// the graph is always tidy: when its shape changes, nodes and edges glide to their new places together.
// What a node looks like is up to the `node` slot; the canvas owns the viewport, the edges and connecting.
const props = withDefaults(defineProps<{
  nodes: N[]
  edges: GraphEdge[]
  selected?: string | null
  /** Nodes can be connected by dragging from their output, and edges removed */
  interactive?: boolean
  /** Nodes can be moved by hand: they stay where they are put until the graph is arranged again */
  draggable?: boolean
  /** The wheel pans the graph instead of scrolling the page: for a canvas that fills the screen */
  scrollPans?: boolean
  nodeWidth?: number
  /** Width of a panel laid over the right edge: the graph is fitted and kept clear of it */
  insetRight?: number
  /** Whether `source` may feed `target`. Defaults to anything but itself */
  canConnect?: (source: string, target: string) => boolean
  label?: string
  labelOf?: (node: N) => string
}>(), {
  selected: null,
  interactive: false,
  draggable: true,
  scrollPans: false,
  nodeWidth: 264,
  insetRight: 0,
  label: 'Graph',
})

const emit = defineEmits<{
  select: [id: string | null]
  connect: [source: string, target: string]
  disconnect: [edgeId: string]
  remove: [id: string]
}>()

defineSlots<{
  node: (props: { node: N, selected: boolean, leaf: boolean }) => any
  empty: () => any
  /** Top left of the canvas */
  tools: () => any
  /** End of the bottom toolbar */
  actions: () => any
}>()

const GAP_X = 48
const GAP_Y = 104
// Height assumed for a node until it has been measured
const GUESS_HEIGHT = 150
const ZOOM_STEP = 1.25

const root = ref<HTMLElement>()
const world = ref<HTMLElement>()
const dots = ref<HTMLElement>()

// Once the user has moved the view, the canvas stops refitting it under their hands
let userMoved = false
// A node just added: brought into view once it has a place, if the user's view would leave it out
let revealOnceMeasured: string | null = null

const reducedMotion = usePreferredReducedMotion()
const motion = () => reducedMotion.value !== 'reduce'

// --- Sizes: measured, never guessed for long ---

const sizes = shallowRef(new Map<string, GraphSize>())
const sizeOf = (id: string): GraphSize => sizes.value.get(id) ?? { width: props.nodeWidth, height: GUESS_HEIGHT }

let observer: ResizeObserver | undefined
let resizeObserver: ResizeObserver | undefined
const observed = new Map<string, HTMLElement>()

function measure(id: string, el: HTMLElement) {
  const width = el.offsetWidth
  const height = el.offsetHeight
  const known = sizes.value.get(id)
  if (known?.width === width && known.height === height)
    return
  const next = new Map(sizes.value)
  next.set(id, { width, height })
  sizes.value = next
}

// Called with the element on every render, and with null before it: only a new element needs work
function bindNode(id: string, el: unknown) {
  if (!(el instanceof HTMLElement) || observed.get(id) === el)
    return
  if (observed.has(id))
    observer?.unobserve(observed.get(id)!)
  observed.set(id, el)
  observer?.observe(el)
  // Synchronous: the first layout already knows the real height
  measure(id, el)
}

// --- Layout and the motion towards it ---

// Where a node was dropped it stays: the others are laid out around the rest, and "arrange" lets go of them all
const manual = shallowRef(new Map<string, GraphPoint>())
const dragging = ref<string | null>(null)

const targets = computed(() => {
  const placed = layoutGraph(
    props.nodes.map(n => n.id),
    props.edges,
    sizeOf,
    { gapX: GAP_X, gapY: GAP_Y },
  )
  for (const [id, at] of manual.value) {
    if (placed.has(id))
      placed.set(id, at)
  }
  return placed
})

const display = new Map<string, { x: SpringState, y: SpringState }>()
const frame = ref(0)
let raf = 0
let last = 0

function positionOf(id: string): GraphPoint {
  void frame.value
  const shown = display.get(id)
  return shown ? { x: shown.x.x, y: shown.y.x } : targets.value.get(id) ?? { x: 0, y: 0 }
}

function rectOf(id: string): GraphRect | null {
  const at = targets.value.get(id)
  if (!at || !sizes.value.has(id))
    return null
  return { ...at, ...sizeOf(id) }
}

function tick(now: number) {
  const dt = Math.min((now - last) / 1000, 1 / 30)
  last = now
  let moving = false
  for (const [id, shown] of display) {
    const to = targets.value.get(id)
    if (!to)
      continue
    springStep(shown.x, to.x, dt)
    springStep(shown.y, to.y, dt)
    if (springSettled(shown.x, to.x) && springSettled(shown.y, to.y)) {
      Object.assign(shown.x, { x: to.x, v: 0 })
      Object.assign(shown.y, { x: to.y, v: 0 })
    }
    else {
      moving = true
    }
  }
  frame.value++
  raf = moving ? requestAnimationFrame(tick) : 0
}

// A node first shows where it belongs; from then on it springs to wherever the layout puts it.
// Only measured nodes are tracked: until then the layout is a guess nobody should see move.
function retarget() {
  for (const id of display.keys()) {
    if (!targets.value.has(id))
      display.delete(id)
  }
  let moving = false
  for (const [id, to] of targets.value) {
    if (!sizes.value.has(id))
      continue
    const shown = display.get(id)
    if (!shown) {
      display.set(id, { x: { x: to.x, v: 0 }, y: { x: to.y, v: 0 } })
      continue
    }
    if (!motion()) {
      Object.assign(shown.x, { x: to.x, v: 0 })
      Object.assign(shown.y, { x: to.y, v: 0 })
    }
    else if (Math.abs(shown.x.x - to.x) > 0.1 || Math.abs(shown.y.x - to.y) > 0.1) {
      moving = true
    }
  }
  if (moving && !raf) {
    last = performance.now()
    raf = requestAnimationFrame(tick)
  }
  frame.value++

  // Without a moved view the graph is refitted anyway, and a refit shows everything
  if (revealOnceMeasured && sizes.value.has(revealOnceMeasured)) {
    if (userMoved)
      reveal(revealOnceMeasured)
    revealOnceMeasured = null
  }
}

watch(targets, retarget, { flush: 'post' })

// A node that goes lingers just long enough to fade, instead of vanishing
const known = new Map<string, N>()
const leaving = shallowRef<{ node: N, at: GraphPoint, key: number }[]>([])
let ghostKey = 0
watch(() => props.nodes.map(n => n.id).join('|'), () => {
  const nodes = props.nodes
  const ids = new Set(nodes.map(n => n.id))
  for (const [id, node] of known) {
    if (ids.has(id))
      continue
    known.delete(id)
    if (manual.value.has(id)) {
      const kept = new Map(manual.value)
      kept.delete(id)
      manual.value = kept
    }
    if (observed.has(id))
      observer?.unobserve(observed.get(id)!)
    observed.delete(id)
    const next = new Map(sizes.value)
    next.delete(id)
    if (motion() && root.value) {
      const entry = { node, at: positionOf(id), key: ++ghostKey }
      leaving.value = [...leaving.value, entry]
      setTimeout(() => leaving.value = leaving.value.filter(g => g !== entry), 160)
    }
    sizes.value = next
  }
  // What was just added is brought into view, if the user has moved the view and it is not
  const added = nodes.filter(n => !known.has(n.id))
  if (known.size > 0 && added.length > 0)
    revealOnceMeasured = added[added.length - 1]!.id
  nodes.forEach(n => known.set(n.id, n))
}, { immediate: true })

// --- Viewport ---

// Not reactive: it changes on every pointer move and only the world's style depends on it
let view: GraphViewport = { x: 0, y: 0, k: 1 }
const zoomPercent = ref(100)
// Hidden until the first fit, so the graph never shows up unplaced
const ready = ref(false)
const panning = ref(false)

function area(): GraphArea {
  // The bottom inset keeps the zoom controls (and the add button under a last node) clear of the graph
  return { width: root.value?.clientWidth ?? 0, height: root.value?.clientHeight ?? 0, insets: { right: props.insetRight, bottom: 24 } }
}

function applyView(animate: boolean) {
  if (!world.value || !dots.value)
    return
  const animated = animate && motion()
  world.value.toggleAttribute('data-animating', animated)
  world.value.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`
  const step = 20 * view.k
  dots.value.style.backgroundPosition = `${view.x}px ${view.y}px`
  dots.value.style.backgroundSize = `${step}px ${step}px`
  // Dots closer than this read as a texture, not a grid
  dots.value.style.opacity = step < 8 ? '0' : '1'
  zoomPercent.value = Math.round(view.k * 100)
}

function setView(next: GraphViewport, { animate = false, user = false } = {}) {
  view = next
  if (user)
    userMoved = true
  applyView(animate)
}

function nodeRects(): GraphRect[] {
  return props.nodes.flatMap((n) => {
    const rect = rectOf(n.id)
    return rect ? [rect] : []
  })
}

function fit(animate = true) {
  const bounds = boundsOf(nodeRects())
  const a = area()
  if (!bounds || a.width === 0 || a.height === 0)
    return false
  setView(fitViewport(bounds, a), { animate })
  return true
}

function refit(animate = true) {
  userMoved = false
  fit(animate)
}

function zoomBy(factor: number, animate = true) {
  const a = area()
  const anchor = { x: (a.width - props.insetRight) / 2, y: a.height / 2 }
  setView(zoomAt(view, view.k * factor, anchor), { animate, user: true })
}

function resetZoom() {
  const a = area()
  setView(zoomAt(view, 1, { x: (a.width - props.insetRight) / 2, y: a.height / 2 }), { animate: true, user: true })
}

function reveal(id: string) {
  const rect = rectOf(id)
  if (!rect)
    return
  const next = revealViewport(view, rect, area())
  if (next !== view)
    setView(next, { animate: true })
}

// Follows the graph while the user has not taken over: first fit in place, later ones glide
const boundsKey = computed(() => {
  const bounds = boundsOf(nodeRects())
  return bounds ? [bounds.x, bounds.y, bounds.width, bounds.height].map(Math.round).join() : ''
})

function followBounds() {
  if (!boundsKey.value)
    return
  if (!ready.value) {
    if (fit(false))
      ready.value = true
  }
  else if (!userMoved) {
    fit(true)
  }
}

watch(boundsKey, followBounds, { flush: 'post' })
watch(() => props.selected, id => id && reveal(id), { flush: 'post' })
watch(() => props.insetRight, () => props.selected && reveal(props.selected), { flush: 'post' })

// A panel beside the canvas closing takes the focus with it: it goes back to the node the panel was about.
// Before the render, while the panel still holds the focus; a node that is gone leaves it to the canvas.
watch(() => props.selected, (_, previous) => {
  const active = document.activeElement
  const host = root.value?.parentElement
  if (props.selected || !previous || !active || root.value!.contains(active) || !host?.contains(active))
    return
  if (props.nodes.some(n => n.id === previous))
    observed.get(previous)?.focus({ preventScroll: true })
  else
    root.value!.focus({ preventScroll: true })
})

// --- Pointer: pan, zoom ---

const connecting = ref<{ source: string, to: GraphPoint, over: string | null, valid: boolean } | null>(null)

const INTERACTIVE = 'button, a, input, textarea, select, [data-graph-ui], [data-port]'

// A press on a node drags that node, a press on the pane drags the view: both wait for 4px of travel,
// so that a click stays a click
let press: {
  id: number
  x: number
  y: number
  moved: boolean
  node: string | null
  /** The press began on an add button: dragging it draws an edge from this node */
  connectFrom: string | null
  /** Where the dragged node was, in the world */
  origin: GraphPoint
} | null = null
let suppressClick = false

function onPointerDown(e: PointerEvent) {
  if ((e.button !== 0 && e.button !== 1) || (e.target as Element).closest(INTERACTIVE))
    return
  const node = props.draggable && e.button === 0
    ? (e.target as Element).closest<HTMLElement>('[data-graph-node]')?.dataset.id ?? null
    : null
  press = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false, node, connectFrom: null, origin: node ? positionOf(node) : { x: 0, y: 0 } }
}

// Controls inside a node (the "+" under it) that also start an edge when dragged hand their press over:
// a click stays theirs, a drag past 4px becomes a connection from this node
function armConnect(e: PointerEvent, id: string) {
  if (!props.interactive || e.button !== 0)
    return
  press = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false, node: null, connectFrom: id, origin: { x: 0, y: 0 } }
}
provide('graphArmConnect', armConnect)

function onPointerMove(e: PointerEvent) {
  if (connecting.value) {
    moveConnect(e)
    return
  }
  if (!press || press.id !== e.pointerId)
    return
  const dx = e.clientX - press.x
  const dy = e.clientY - press.y
  if (!press.moved) {
    if (Math.hypot(dx, dy) < 4)
      return
    press.moved = true
    // Captured only now: a plain click must still reach the node under the pointer
    root.value?.setPointerCapture(e.pointerId)
    if (press.connectFrom) {
      connecting.value = { source: press.connectFrom, to: worldPoint(e), over: null, valid: false }
      moveConnect(e)
      return
    }
    if (press.node)
      dragging.value = press.node
    else
      panning.value = true
    // Whoever moves things by hand does not want the canvas to refit them
    userMoved = true
  }

  if (press.node) {
    // From where the node started, so a long drag does not accumulate rounding
    const at = { x: press.origin.x + dx / view.k, y: press.origin.y + dy / view.k }
    const next = new Map(manual.value)
    next.set(press.node, at)
    manual.value = next
    // The node is in the hand, not on a spring: it follows the pointer exactly
    const shown = display.get(press.node)
    if (shown) {
      Object.assign(shown.x, { x: at.x, v: 0 })
      Object.assign(shown.y, { x: at.y, v: 0 })
    }
    frame.value++
    return
  }

  setView({ ...view, x: view.x + dx, y: view.y + dy }, { user: true })
  press.x = e.clientX
  press.y = e.clientY
}

function onPointerCancel() {
  cancelConnect()
  press = null
  panning.value = false
  dragging.value = null
}

function onPointerUp(e: PointerEvent) {
  if (connecting.value)
    endConnect(e)
  if (!press || press.id !== e.pointerId)
    return
  if (press.moved) {
    root.value?.releasePointerCapture(e.pointerId)
    // The click that follows a drag is not a click
    suppressClick = true
    setTimeout(() => suppressClick = false)
  }
  press = null
  panning.value = false
  dragging.value = null
}

// Lets go of every node placed by hand: they spring back to the layout, and the view follows again
function arrange() {
  if (manual.value.size === 0)
    return
  manual.value = new Map()
  refit()
}

// Pinch on a trackpad arrives as ctrl + wheel. A plain wheel is left to the page, unless the canvas
// fills the screen: it sits inside a form, and stealing its scroll would trap whoever passes over it.
useEventListener(root, 'wheel', (e: WheelEvent) => {
  if (!e.ctrlKey && !e.metaKey) {
    if (!props.scrollPans)
      return
    e.preventDefault()
    setView({ ...view, x: view.x - e.deltaX, y: view.y - e.deltaY }, { user: true })
    return
  }
  e.preventDefault()
  const rect = root.value!.getBoundingClientRect()
  const delta = Math.max(-24, Math.min(24, -e.deltaY)) * 0.01
  setView(zoomAt(view, view.k * Math.exp(delta), { x: e.clientX - rect.left, y: e.clientY - rect.top }), { user: true })
}, { passive: false })

function onClick(e: MouseEvent) {
  if (suppressClick)
    return
  const target = e.target as Element
  if (target.closest(INTERACTIVE))
    return
  const node = target.closest<HTMLElement>('[data-graph-node]')
  emit('select', node?.dataset.id ?? null)
}

// --- Connecting ---

function worldPoint(e: PointerEvent): GraphPoint {
  const rect = root.value!.getBoundingClientRect()
  return { x: (e.clientX - rect.left - view.x) / view.k, y: (e.clientY - rect.top - view.y) / view.k }
}

function startConnect(e: PointerEvent, id: string) {
  if (!props.interactive || e.button !== 0)
    return
  e.preventDefault()
  // The root keeps the pointer: the move and the release arrive there, wherever the pointer is
  root.value!.setPointerCapture(e.pointerId)
  connecting.value = { source: id, to: worldPoint(e), over: null, valid: false }
}

function moveConnect(e: PointerEvent) {
  const state = connecting.value
  if (!state)
    return
  const over = document.elementFromPoint(e.clientX, e.clientY)?.closest<HTMLElement>('[data-graph-node]')?.dataset.id ?? null
  const valid = !!over && over !== state.source && (props.canConnect?.(state.source, over) ?? true)
  connecting.value = { ...state, to: worldPoint(e), over, valid }
}

function endConnect(e: PointerEvent) {
  const state = connecting.value
  if (!state)
    return
  moveConnect(e)
  const { source, over, valid } = connecting.value!
  connecting.value = null
  if (valid && over)
    emit('connect', source, over)
}

function cancelConnect() {
  connecting.value = null
}

// --- Keyboard ---

function onKeydown(e: KeyboardEvent) {
  if (e.metaKey || e.ctrlKey || e.altKey)
    return
  const el = e.target as HTMLElement
  // A field inside the canvas (the agent picker, in full screen) keeps its own keys
  if (el.closest('input, textarea, select, [contenteditable]'))
    return
  const onNode = el.matches('[data-graph-node]')
  // A key held down repeats: the view follows each press at once instead of gliding behind it
  switch (e.key) {
    case '+':
    case '=':
      zoomBy(ZOOM_STEP, false)
      break
    case '-':
      zoomBy(1 / ZOOM_STEP, false)
      break
    case '0':
      refit(false)
      break
    case 'Escape':
      // Handled here first: an expanded canvas only closes on an Escape nobody used
      if (connecting.value) {
        cancelConnect()
        e.preventDefault()
      }
      else if (props.selected) {
        emit('select', null)
        e.preventDefault()
      }
      break
    case 'Enter':
    case ' ':
      if (!onNode)
        return
      e.preventDefault()
      emit('select', el.dataset.id!)
      break
    case 'Delete':
    case 'Backspace': {
      // The focused node, or else the selected one (a click selects a node without always focusing it)
      const id = onNode ? el.dataset.id! : props.selected
      if (!id || !props.interactive)
        return
      e.preventDefault()
      emit('remove', id)
      // The removed node took the focus with it: the canvas keeps it, for the next key
      root.value!.focus({ preventScroll: true })
      break
    }
  }
}

// --- Edges ---

const sources = computed(() => new Set(props.edges.map(e => e.source)))
const hoveredEdge = ref<string | null>(null)

const shapes = computed(() => {
  const present = new Set(props.nodes.map(n => n.id))
  const edges = props.edges.filter(edge => present.has(edge.source) && present.has(edge.target))
  const shown = (id: string): GraphRect => ({ ...positionOf(id), ...sizeOf(id) })
  const settled = (id: string): GraphRect | undefined => {
    const at = targets.value.get(id)
    return at ? { ...at, ...sizeOf(id) } : undefined
  }
  const routes = routeEdges(edges, shown, settled, props.nodes.map(n => n.id))
  return edges
    .flatMap((edge) => {
      const route = routes.get(edge.id)
      return route
        ? [{ edge, ...route, active: !!props.selected && (edge.source === props.selected || edge.target === props.selected) }]
        : []
    })
})

const preview = computed(() => {
  const state = connecting.value
  if (!state)
    return null
  const from = positionOf(state.source)
  const start = { x: from.x + sizeOf(state.source).width / 2, y: from.y + sizeOf(state.source).height }
  // Snaps onto the node it would connect to
  const snapped = state.valid && state.over ? positionOf(state.over) : null
  const end = snapped ? { x: snapped.x + sizeOf(state.over!).width / 2, y: snapped.y - ARROW_GAP } : state.to
  return { d: edgePath(start, end).d, valid: state.valid }
})

// --- Classes: what each piece looks like in its current state ---

// An edge that appears (a connection made, an agent added) is drawn from its source on, then gets its arrowhead.
// Before the first fit, edges simply are
const edgeLineClass = computed(() => ready.value
  ? '[stroke-dasharray:1] transition-[stroke,stroke-dashoffset] duration-[150ms,360ms] ease-out starting:[stroke-dashoffset:1] motion-reduce:duration-0'
  : 'transition-[stroke] duration-150 ease-out')
const edgeArrowClass = computed(() => ready.value
  ? 'transition-[stroke,opacity] duration-[150ms,200ms] delay-[0ms,160ms] ease-out starting:opacity-0 motion-reduce:duration-0'
  : 'transition-[stroke] duration-150 ease-out')

function nodeClass(id: string) {
  const state = connecting.value
  const source = state?.source === id
  const target = state?.over === id && state.valid
  const rejected = state?.over === id && !state.valid && !source
  return [
    // A node added after the first fit eases in; the ones that were there simply are
    ready.value && 'transition-[opacity,scale] duration-200 ease-out starting:scale-95 starting:opacity-0 motion-reduce:starting:scale-100',
    // In the hand: above the others, lifted
    dragging.value === id && 'z-2 shadow-[0_18px_32px_-12px_rgb(0_0_0/0.28)]',
    // While connecting, what can take the edge says so, and what cannot stays quiet
    state && !source && !target && 'opacity-55',
    target && 'outline-2 outline-offset-3 outline-inverted',
    !state ? 'cursor-pointer' : rejected ? 'cursor-not-allowed' : 'cursor-crosshair',
  ]
}

// Ports: where edges leave and enter. The input only shows when something is being connected: otherwise the
// arrowhead is enough
function portInClass(id: string) {
  const state = connecting.value
  return state?.over === id && state.valid ? 'scale-150 border-(--ui-text-highlighted) opacity-100' : 'border-(--graph-edge) opacity-0'
}

function portOutClass(id: string) {
  return [
    connecting.value?.source === id ? 'scale-145 border-(--ui-text-highlighted) bg-(--ui-text-highlighted)' : 'border-(--graph-edge) bg-default',
    // A hit area well past the dot: it is small to see, not to grab
    props.interactive && 'cursor-crosshair before:absolute before:-inset-2.5 hover:scale-145 hover:border-(--ui-text-highlighted) hover:bg-(--ui-text-highlighted)',
  ]
}

const portClass = 'absolute left-1/2 size-[7px] rounded-full border-[1.5px] transition-[border-color,scale,opacity] duration-150 ease-out'

// --- Lifecycle ---

onMounted(() => {
  observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const el = entry.target as HTMLElement
      if (el.dataset.id && el.isConnected)
        measure(el.dataset.id, el)
    }
  })
  observed.forEach(el => observer!.observe(el))
  applyView(false)
  retarget()

  // The canvas itself resizing (window, layout): follow, unless the user has taken over
  resizeObserver = new ResizeObserver(() => {
    if (!ready.value)
      followBounds()
    else if (!userMoved)
      fit(false)
  })
  resizeObserver.observe(root.value!)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  resizeObserver?.disconnect()
  cancelAnimationFrame(raf)
})

defineExpose({ fit: refit, zoomBy })
</script>

<template>
  <div
    ref="root"
    class="relative size-full touch-none overflow-hidden bg-muted outline-none select-none [--graph-edge-active:var(--ui-text-highlighted)] [--graph-edge-hover:var(--ui-text-muted)] [--graph-edge:var(--ui-border-accented)]"
    :class="{ 'cursor-grabbing! **:cursor-grabbing!': panning || !!dragging, 'cursor-crosshair': !!connecting }"
    role="group"
    :aria-label="label"
    tabindex="0"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerCancel"
    @click="onClick"
    @keydown="onKeydown"
  >
    <!-- The pane is not a button: it keeps the arrow, and only turns into a hand while it is being dragged.
         Nodes can be clicked, so they say so. The dots are a texture, not a grid to read: they stay well below the
         edges and the cards in weight -->
    <div
      ref="dots"
      class="pointer-events-none absolute inset-0 bg-[image:radial-gradient(circle,color-mix(in_oklab,var(--ui-border-accented)_38%,transparent)_1px,transparent_1.25px)] transition-opacity duration-150 ease-out"
      aria-hidden="true"
    />

    <!-- Hidden until the first fit places the graph: then it fades in, once -->
    <div
      ref="world"
      class="absolute top-0 left-0 origin-top-left data-animating:transition-[transform,opacity] data-animating:duration-200 data-animating:ease-out"
      :class="ready ? 'opacity-100 transition-opacity duration-200 ease-out' : 'opacity-0'"
    >
      <svg
        class="pointer-events-none absolute top-0 left-0 size-px overflow-visible fill-none stroke-[1.5] [stroke-linecap:round] [stroke-linejoin:round]"
        aria-hidden="true"
      >
        <g v-for="shape in shapes" :key="shape.edge.id" :class="hoveredEdge === shape.edge.id ? 'stroke-(--graph-edge-hover)' : 'stroke-(--graph-edge)'">
          <path class="stroke-transparent stroke-[18] [pointer-events:stroke]" :d="shape.d" @pointerenter="hoveredEdge = shape.edge.id" @pointerleave="hoveredEdge = null" />
          <path :class="edgeLineClass" :d="shape.d" pathLength="1" />
          <path :class="edgeArrowClass" :d="shape.arrow" />
        </g>
        <!-- The edges of the selected node are drawn again on top, in the highlight colour. A layer of its own,
             always there and faded in: reordering the edges above would move their elements, and a moved
             element plays its entrance again -->
        <g class="stroke-(--graph-edge-active)">
          <g
            v-for="shape in shapes"
            :key="shape.edge.id"
            class="transition-opacity duration-150 ease-out"
            :class="shape.active ? 'opacity-100' : 'opacity-0'"
          >
            <path :d="shape.d" />
            <path :d="shape.arrow" />
          </g>
        </g>
        <path
          v-if="preview"
          class="transition-[stroke] duration-150 ease-out"
          :class="preview.valid ? 'stroke-(--graph-edge-active)' : 'stroke-(--graph-edge-hover) [stroke-dasharray:4_5]'"
          :d="preview.d"
        />
      </svg>

      <div
        v-for="node in nodes"
        :key="node.id"
        :ref="(el) => bindNode(node.id, el)"
        class="group/graph-node absolute top-0 left-0 rounded-[14px] select-none focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-inverted"
        :class="nodeClass(node.id)"
        :style="{ translate: `${positionOf(node.id).x}px ${positionOf(node.id).y}px`, width: `${nodeWidth}px` }"
        :data-id="node.id"
        data-graph-node
        role="group"
        :aria-label="labelOf?.(node)"
        :aria-current="node.id === selected || undefined"
        tabindex="0"
      >
        <slot name="node" :node="node" :selected="node.id === selected" :leaf="!sources.has(node.id)" />
        <span :class="[portClass, portInClass(node.id)]" class="top-0 -translate-1/2 bg-default" aria-hidden="true" />
        <span
          :class="[portClass, portOutClass(node.id)]"
          class="bottom-0 -translate-x-1/2 translate-y-1/2"
          data-port
          aria-hidden="true"
          @pointerdown="startConnect($event, node.id)"
        />
      </div>

      <div
        v-for="ghost in leaving"
        :key="`leaving-${ghost.key}`"
        class="pointer-events-none absolute top-0 left-0 scale-[0.96] rounded-[14px] opacity-0 transition-[opacity,scale] duration-150 ease-out starting:scale-100 starting:opacity-100"
        :style="{ translate: `${ghost.at.x}px ${ghost.at.y}px`, width: `${nodeWidth}px` }"
        aria-hidden="true"
      >
        <slot name="node" :node="ghost.node" :selected="false" :leaf="true" />
      </div>

      <!-- Pills sit above the nodes: an edge label, or the button that removes the edge -->
      <template v-for="shape in shapes" :key="`pill-${shape.edge.id}`">
        <div
          v-if="shape.edge.label || (interactive && shape.edge.deletable !== false)"
          class="pointer-events-none absolute top-0 left-0"
          :style="{ translate: `${shape.label.x}px ${shape.label.y}px` }"
        >
          <div class="pointer-events-auto flex -translate-1/2" data-graph-ui @pointerenter="hoveredEdge = shape.edge.id" @pointerleave="hoveredEdge = null">
            <span
              v-if="shape.edge.label"
              class="block max-w-44 truncate rounded-md border bg-default px-1.5 py-0.5 font-mono text-[11px] leading-4 transition-colors duration-150 ease-out"
              :class="hoveredEdge === shape.edge.id || shape.active ? 'border-accented text-toned' : 'border-default text-muted'"
              :title="shape.edge.label"
            >{{ shape.edge.label }}</span>
            <button
              v-else
              type="button"
              class="relative grid size-4.5 place-items-center rounded-full border bg-default transition-[color,border-color,scale] duration-120 ease-out before:absolute before:-inset-1 hover:border-error hover:text-error active:scale-[0.92] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inverted"
              :class="hoveredEdge === shape.edge.id ? 'border-accented text-highlighted' : 'border-default text-muted'"
              :aria-label="`${shape.edge.removeLabel ?? 'Remove connection'}${shape.edge.name ? `: ${shape.edge.name}` : ''}`"
              :title="shape.edge.removeLabel ?? 'Remove connection'"
              @click="emit('disconnect', shape.edge.id)"
            >
              <UIcon name="i-ph-link-break-bold" class="size-3" />
            </button>
          </div>
        </div>
      </template>
    </div>

    <div v-if="nodes.length === 0" class="pointer-events-none absolute inset-0 flex items-center justify-center">
      <slot name="empty" />
    </div>

    <div v-if="$slots.tools" class="absolute top-3 left-3 z-10 flex items-center gap-2" data-graph-ui>
      <slot name="tools" />
    </div>

    <div class="pointer-events-auto absolute bottom-3 left-3 z-10" data-graph-ui>
      <UITooltipGroup>
        <div class="flex items-center gap-px rounded-lg border border-default bg-default p-0.5 shadow-xs">
          <GraphControl label="Zoom out" icon="i-ph-minus-bold" kbd="-" :disabled="zoomPercent <= Math.round(GRAPH_MIN_ZOOM * 100)" @click="zoomBy(1 / ZOOM_STEP)" />
          <GraphControl label="Reset zoom" class="w-11 text-xs tabular-nums" @click="resetZoom">
            {{ zoomPercent }}%
          </GraphControl>
          <GraphControl label="Zoom in" icon="i-ph-plus-bold" kbd="+" :disabled="zoomPercent >= Math.round(GRAPH_MAX_ZOOM * 100)" @click="zoomBy(ZOOM_STEP)" />
          <span class="mx-0.5 h-4 w-px bg-border" aria-hidden="true" />
          <GraphControl label="Fit to view" icon="i-ph-corners-out-bold" kbd="0" @click="refit()" />
          <GraphControl v-if="draggable" label="Arrange nodes" icon="i-ph-tree-structure-bold" :disabled="manual.size === 0" @click="arrange" />
          <slot name="actions" />
        </div>
      </UITooltipGroup>
    </div>
  </div>
</template>
