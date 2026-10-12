<script setup lang="ts">
import { useEventListener, usePreferredReducedMotion } from '@vueuse/core'

// Holds a canvas on the page, and lets it fill the screen: a graph with a form column and a summary
// around it is cramped, and the one thing a graph wants is room. The page keeps its place (the frame
// leaves a blank of its own height behind), and the frame morphs between the two: its real box grows
// from the one on the page to the one on screen, and the graph inside keeps fitting it as it goes,
// so nothing is stretched. Occasional, so it can afford to be seen, but it stays quick.
withDefaults(defineProps<{
  height?: string
  /** Names the frame while it fills the screen */
  label?: string
}>(), {
  height: 'clamp(480px, 68dvh, 780px)',
  label: 'Graph',
})

defineSlots<{
  default: (props: { expanded: boolean, settled: boolean, toggle: () => void }) => any
}>()

const DURATION = 280
const EASING = 'cubic-bezier(0.23, 1, 0.32, 1)'
const SHADOW = '0 25px 50px -12px rgb(0 0 0 / 0.25)'
const NO_SHADOW = '0 25px 50px -12px rgb(0 0 0 / 0)'

const expanded = ref(false)
// The backdrop leads the frame: it fades in as it starts to grow, and out as it starts to shrink
const dimmed = ref(false)
// Full screen and at rest: false while the frame is on its way, in either direction. What is shown
// twice (on the page and over the canvas) belongs to the page until the frame has really landed
const settled = ref(false)
const panel = ref<HTMLElement>()
const holder = ref<HTMLElement>()
const reducedMotion = usePreferredReducedMotion()

let running: Animation | undefined
// The corner radius of the frame on the page, to come back to exactly
let pageRadius = ''
const radiusOf = (el: HTMLElement) => getComputedStyle(el).borderTopLeftRadius

function look(rect: DOMRect, radius: string, shadow: string) {
  return {
    top: `${rect.top}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    height: `${rect.height}px`,
    borderRadius: radius,
    boxShadow: shadow,
  }
}

function glide(from: DOMRect, to: DOMRect, radii: [string, string], shadows: [string, string]) {
  running = panel.value!.animate(
    [look(from, radii[0], shadows[0]), look(to, radii[1], shadows[1])],
    { duration: DURATION, easing: EASING, fill: 'both' },
  )
  return running
}

async function toggle() {
  const el = panel.value
  if (!el || !holder.value)
    return
  // Where it is right now, mid-glide included: a press while it moves turns it around from there
  const from = el.getBoundingClientRect()
  const fromRadius = radiusOf(el)
  running?.cancel()
  const animate = reducedMotion.value !== 'reduce'

  if (!expanded.value) {
    pageRadius = fromRadius
    dimmed.value = true
    expanded.value = true
    await nextTick()
    if (!animate) {
      settled.value = true
      return
    }
    const anim = glide(from, el.getBoundingClientRect(), [fromRadius, radiusOf(el)], [NO_SHADOW, SHADOW])
    const done = await anim.finished.then(() => true, () => false)
    // Settled on the real thing: nothing left to hold
    if (running === anim)
      anim.cancel()
    // Turned around mid-glide: it never landed
    if (done)
      settled.value = true
    return
  }

  dimmed.value = false
  settled.value = false
  if (animate) {
    const anim = glide(from, holder.value.getBoundingClientRect(), [fromRadius, pageRadius], [SHADOW, NO_SHADOW])
    const done = await anim.finished.then(() => true, () => false)
    // Interrupted by another press: that one owns the frame now
    if (!done)
      return
  }
  expanded.value = false
  await nextTick()
  // Back on the page, where the holder is: the pinned values would now point at the screen
  running?.cancel()
}

// The canvas takes the Escape it can use (deselecting, cancelling a connection) and says so
useEventListener('keydown', (e: KeyboardEvent) => {
  if (e.key === 'Escape' && expanded.value && !e.defaultPrevented)
    toggle()
})
</script>

<template>
  <div ref="holder" class="relative" :style="{ height }">
    <Transition
      enter-active-class="transition-opacity duration-200 ease-out motion-reduce:transition-none"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-200 ease-out motion-reduce:transition-none"
      leave-to-class="opacity-0"
    >
      <div v-if="dimmed" class="fixed inset-0 z-50 bg-black/40" aria-hidden="true" @click="toggle" />
    </Transition>

    <!-- Isolated and clipped to its radius. The border is drawn over the content rather than around it: the
         canvas, its overlays and the compositing of its moving layers can never paint across a corner -->
    <div
      ref="panel"
      class="group/frame isolate overflow-hidden bg-muted"
      :class="expanded ? 'fixed inset-3 z-50 rounded-xl shadow-2xl' : 'absolute inset-0 rounded-lg'"
      :role="expanded ? 'dialog' : undefined"
      :aria-modal="expanded || undefined"
      :aria-label="expanded ? label : undefined"
    >
      <slot :expanded="expanded" :settled="settled" :toggle="toggle" />
      <!-- Also where the keyboard focus of the canvas shows: a ring on the canvas itself would stay square under the radius -->
      <div
        class="pointer-events-none absolute inset-0 z-30 rounded-[inherit] border border-default group-has-[.graph:focus-visible]/frame:ring-2 group-has-[.graph:focus-visible]/frame:ring-inverted group-has-[.graph:focus-visible]/frame:ring-inset"
        aria-hidden="true"
      />
    </div>
  </div>
</template>
