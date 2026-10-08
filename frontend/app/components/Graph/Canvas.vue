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
  world.value.classList.toggle('is-animating', animated)
  dots.value.classList.toggle('is-animating', animated)
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

function refit() {
  userMoved = false
  fit(true)
}

function zoomBy(factor: number) {
  const a = area()
  const anchor = { x: (a.width - props.insetRight) / 2, y: a.height / 2 }
  setView(zoomAt(view, view.k * factor, anchor), { animate: true, user: true })
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
  const onNode = el.matches('[data-graph-node]')
  switch (e.key) {
    case '+':
    case '=':
      zoomBy(ZOOM_STEP)
      break
    case '-':
      zoomBy(1 / ZOOM_STEP)
      break
    case '0':
      refit()
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
    case 'Backspace':
      if (!onNode || !props.interactive)
        return
      e.preventDefault()
      emit('remove', el.dataset.id!)
      break
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
    class="graph relative size-full overflow-hidden bg-muted outline-none select-none"
    :class="{ 'is-ready': ready, 'is-panning': panning, 'is-dragging': !!dragging, 'is-connecting': !!connecting }"
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
    <div ref="dots" class="graph-dots pointer-events-none absolute inset-0" aria-hidden="true" />

    <div ref="world" class="graph-world absolute top-0 left-0 origin-top-left">
      <svg class="graph-edges" aria-hidden="true">
        <g
          v-for="shape in shapes"
          :key="shape.edge.id"
          class="graph-edge"
          :class="{ 'is-active': shape.active, 'is-hovered': hoveredEdge === shape.edge.id }"
        >
          <path class="graph-edge-hit" :d="shape.d" @pointerenter="hoveredEdge = shape.edge.id" @pointerleave="hoveredEdge = null" />
          <path class="graph-edge-line" :d="shape.d" pathLength="1" />
          <path class="graph-edge-arrow" :d="shape.arrow" />
        </g>
        <!-- The edges of the selected node are drawn again on top, in the highlight colour. A layer of its own,
             always there and faded in: reordering the edges above would move their elements, and a moved
             element plays its entrance again -->
        <g class="graph-edges-highlight">
          <g v-for="shape in shapes" :key="shape.edge.id" class="graph-edge-highlight" :class="{ 'is-active': shape.active }">
            <path :d="shape.d" />
            <path :d="shape.arrow" />
          </g>
        </g>
        <path v-if="preview" class="graph-edge-line graph-edge-preview" :class="{ 'is-valid': preview.valid }" :d="preview.d" />
      </svg>

      <div
        v-for="node in nodes"
        :key="node.id"
        :ref="(el) => bindNode(node.id, el)"
        class="graph-node"
        :class="{
          'is-selected': node.id === selected,
          'is-dragging': dragging === node.id,
          'is-source': connecting?.source === node.id,
          'is-target': connecting?.over === node.id && connecting.valid,
          'is-rejected': connecting?.over === node.id && !connecting.valid && connecting.source !== node.id,
        }"
        :style="{ translate: `${positionOf(node.id).x}px ${positionOf(node.id).y}px`, width: `${nodeWidth}px` }"
        :data-id="node.id"
        data-graph-node
        role="group"
        :aria-label="labelOf?.(node)"
        tabindex="0"
      >
        <slot name="node" :node="node" :selected="node.id === selected" :leaf="!sources.has(node.id)" />
        <span class="graph-port graph-port-in" aria-hidden="true" />
        <span
          class="graph-port graph-port-out"
          :class="{ 'is-interactive': interactive }"
          data-port
          aria-hidden="true"
          @pointerdown="startConnect($event, node.id)"
        />
      </div>

      <div
        v-for="ghost in leaving"
        :key="`leaving-${ghost.key}`"
        class="graph-node is-leaving"
        :style="{ translate: `${ghost.at.x}px ${ghost.at.y}px`, width: `${nodeWidth}px` }"
        aria-hidden="true"
      >
        <slot name="node" :node="ghost.node" :selected="false" :leaf="true" />
      </div>

      <!-- Pills sit above the nodes: an edge label, or the button that removes the edge -->
      <template v-for="shape in shapes" :key="`pill-${shape.edge.id}`">
        <div
          v-if="shape.edge.label || (interactive && shape.edge.deletable !== false)"
          class="graph-pill"
          :class="{ 'is-hovered': hoveredEdge === shape.edge.id, 'is-active': shape.active }"
          :style="{ translate: `${shape.label.x}px ${shape.label.y}px` }"
        >
          <div class="graph-pill-body" data-graph-ui @pointerenter="hoveredEdge = shape.edge.id" @pointerleave="hoveredEdge = null">
            <span v-if="shape.edge.label" class="graph-pill-label" :title="shape.edge.label">{{ shape.edge.label }}</span>
            <button
              v-else
              type="button"
              class="graph-pill-remove"
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
          <span class="mx-0.5 h-4 w-px bg-[var(--ui-border)]" aria-hidden="true" />
          <GraphControl label="Fit to view" icon="i-ph-corners-out-bold" kbd="0" @click="refit" />
          <GraphControl v-if="draggable" label="Arrange nodes" icon="i-ph-tree-structure-bold" :disabled="manual.size === 0" @click="arrange" />
          <slot name="actions" />
        </div>
      </UITooltipGroup>
    </div>
  </div>
</template>

<style scoped>
.graph {
  --graph-edge: var(--ui-border-accented);
  --graph-edge-hover: var(--ui-text-muted);
  --graph-edge-active: var(--ui-text-highlighted);
  touch-action: none;
}

/* The pane is not a button: it keeps the arrow, and only turns into a hand while it is being dragged.
   Nodes can be clicked, so they say so. */
.graph.is-panning,
.graph.is-panning *,
.graph.is-dragging,
.graph.is-dragging * {
  cursor: grabbing !important;
}

.graph.is-connecting,
.graph.is-connecting .graph-node {
  cursor: crosshair;
}

.graph-dots {
  /* A texture, not a grid to read: the dots stay well below the edges and the cards in weight */
  background-image: radial-gradient(circle, color-mix(in oklab, var(--ui-border-accented) 38%, transparent) 1px, transparent 1.25px);
  transition: opacity 150ms var(--ease-out);
}

.graph-dots.is-animating {
  transition: opacity 150ms var(--ease-out), background-position 320ms var(--ease-out), background-size 320ms var(--ease-out);
}

/* Hidden until the first fit places the graph: then it fades in, once */
.graph-world {
  opacity: 0;
}

.graph.is-ready .graph-world {
  opacity: 1;
  transition: opacity 200ms var(--ease-out);
}

.graph-world.is-animating {
  transition: transform 320ms var(--ease-out), opacity 200ms var(--ease-out);
}

/* Edges ------------------------------------------------------------------ */

.graph-edges {
  position: absolute;
  top: 0;
  left: 0;
  width: 1px;
  height: 1px;
  overflow: visible;
  pointer-events: none;
}

.graph-edge-line,
.graph-edge-arrow {
  fill: none;
  stroke: var(--graph-edge);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: stroke 150ms var(--ease-out);
}

.graph-edge-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 18;
  pointer-events: stroke;
}

.graph-edge.is-hovered .graph-edge-line,
.graph-edge.is-hovered .graph-edge-arrow {
  stroke: var(--graph-edge-hover);
}

.graph-edge-highlight {
  fill: none;
  stroke: var(--graph-edge-active);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0;
  transition: opacity 150ms var(--ease-out);
}

.graph-edge-highlight.is-active {
  opacity: 1;
}

.graph-edge-preview {
  stroke: var(--graph-edge-hover);
  stroke-dasharray: 4 5;
}

.graph-edge-preview.is-valid {
  stroke: var(--graph-edge-active);
  stroke-dasharray: none;
}

/* An edge that appears (a connection made, an agent added) is drawn from its source on, then gets its arrowhead */
.graph.is-ready .graph-edge-line {
  stroke-dasharray: 1;
  stroke-dashoffset: 0;
  transition: stroke 150ms var(--ease-out), stroke-dashoffset 360ms var(--ease-out);

  @starting-style {
    stroke-dashoffset: 1;
  }
}

.graph.is-ready .graph-edge-arrow {
  transition: stroke 150ms var(--ease-out), opacity 200ms var(--ease-out) 160ms;

  @starting-style {
    opacity: 0;
  }
}

.graph.is-ready .graph-edge-preview {
  stroke-dasharray: 4 5;
}

.graph.is-ready .graph-edge-preview.is-valid {
  stroke-dasharray: none;
}

/* Pills -------------------------------------------------------------------- */

.graph-pill {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.graph-pill-body {
  translate: -50% -50%;
  display: flex;
  pointer-events: auto;
}

.graph-pill-label {
  display: block;
  max-width: 11rem;
  overflow: hidden;
  border: 1px solid var(--ui-border);
  border-radius: 6px;
  background: var(--ui-bg);
  padding: 0.125rem 0.375rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  line-height: 1rem;
  color: var(--ui-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: border-color 150ms var(--ease-out), color 150ms var(--ease-out);
}

.graph-pill.is-hovered .graph-pill-label,
.graph-pill.is-active .graph-pill-label {
  border-color: var(--ui-border-accented);
  color: var(--ui-text-toned);
}

.graph-pill-remove {
  display: grid;
  width: 1.125rem;
  height: 1.125rem;
  place-items: center;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: var(--ui-bg);
  color: var(--ui-text-dimmed);
  transition: color 120ms var(--ease-out), border-color 120ms var(--ease-out), scale 120ms var(--ease-out);
}

/* Always there, quietly: a dependency between agents is something to see and to be able to cut */
.graph-pill.is-hovered .graph-pill-remove {
  border-color: var(--ui-border-accented);
  color: var(--ui-text-highlighted);
}

.graph-pill-remove:hover {
  border-color: var(--ui-error);
  color: var(--ui-error);
}

.graph-pill-remove:active {
  scale: 0.92;
}

.graph-pill-remove:focus-visible {
  outline: 2px solid var(--ui-border-inverted);
  outline-offset: 2px;
}

/* Nodes -------------------------------------------------------------------- */

.graph-node {
  position: absolute;
  top: 0;
  left: 0;
  border-radius: 14px;
  outline: none;
  cursor: pointer;
  user-select: none;
}

/* In the hand: above the others, lifted */
.graph-node.is-dragging {
  z-index: 2;
  box-shadow: 0 18px 32px -12px rgb(0 0 0 / 0.28);
  transition: box-shadow 150ms var(--ease-out);
}

/* A node added after the first fit eases in; the ones that were there simply are */
.graph.is-ready .graph-node:not(.is-leaving) {
  transition: opacity 200ms var(--ease-out), scale 200ms var(--ease-out);

  @starting-style {
    opacity: 0;
    scale: 0.95;
  }
}

.graph-node.is-leaving {
  opacity: 0;
  scale: 0.96;
  pointer-events: none;
  transition: opacity 150ms var(--ease-out), scale 150ms var(--ease-out);

  @starting-style {
    opacity: 1;
    scale: 1;
  }
}

.graph-node:focus-visible {
  outline: 2px solid var(--ui-border-inverted);
  outline-offset: 3px;
}

/* While connecting, what can take the edge says so, and what cannot stays quiet */
.graph.is-connecting .graph-node:not(.is-source, .is-target) {
  opacity: 0.55;
  transition: opacity 150ms var(--ease-out);
}

.graph-node.is-target {
  outline: 2px solid var(--ui-border-inverted);
  outline-offset: 3px;
}

.graph-node.is-rejected {
  cursor: not-allowed;
}

/* Ports: where edges leave and enter */
.graph-port {
  position: absolute;
  left: 50%;
  width: 7px;
  height: 7px;
  border: 1.5px solid var(--graph-edge);
  border-radius: 999px;
  background: var(--ui-bg);
  transition: border-color 150ms var(--ease-out), scale 150ms var(--ease-out), opacity 150ms var(--ease-out);
}

.graph-port-out {
  bottom: 0;
  translate: -50% 50%;
}

/* The input only shows when something is being connected: otherwise the arrowhead is enough */
.graph-port-in {
  top: 0;
  translate: -50% -50%;
  opacity: 0;
}

.graph.is-connecting .graph-node.is-target .graph-port-in {
  border-color: var(--ui-text-highlighted);
  opacity: 1;
  scale: 1.5;
}

.graph-port-out.is-interactive {
  cursor: crosshair;
}

/* A hit area well past the dot: it is small to see, not to grab */
.graph-port-out.is-interactive::before {
  position: absolute;
  inset: -10px;
  content: '';
}

.graph-node.is-source .graph-port-out {
  border-color: var(--ui-text-highlighted);
  background: var(--ui-text-highlighted);
  scale: 1.45;
}

@media (hover: hover) and (pointer: fine) {
  .graph-port-out.is-interactive:hover {
    border-color: var(--ui-text-highlighted);
    background: var(--ui-text-highlighted);
    scale: 1.45;
  }
}

@media (prefers-reduced-motion: reduce) {
  .graph.is-ready .graph-edge-line,
  .graph.is-ready .graph-edge-arrow,
  .graph-world.is-animating {
    transition-duration: 0ms;
  }

  .graph.is-ready .graph-node:not(.is-leaving) {
    @starting-style {
      scale: 1;
    }
  }
}
</style>
