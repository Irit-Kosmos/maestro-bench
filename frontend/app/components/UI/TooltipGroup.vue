<script setup lang="ts">
import { useEventListener } from '@vueuse/core'

// One tooltip for a row of controls: it slides from one control to the next instead of each fading in over
// the last. Controls opt in with data-tooltip="…" (and data-tooltip-kbds="meta,I" for a shortcut).
defineSlots<{ default?: any }>()
provide(tooltipGroupKey, true)

// Same timings as the app-wide UTooltip provider (app.vue)
const OPEN_DELAY = 500
const SKIP_DELAY = 300
// Leaving one control for the next, or for the tooltip itself, crosses a gap: it waits that long before closing
const CLOSE_GRACE = 100
const OFFSET = 6
const MARGIN = 8

const id = useId()
const root = ref<HTMLElement>()
const tooltip = ref<HTMLElement>()

const trigger = shallowRef<HTMLElement | null>(null)
const text = ref('')
const kbds = ref<string[]>([])
const open = ref(false)
// Once on screen, the tooltip moves to its next control rather than reappearing
const sliding = ref(false)
const position = ref({ x: 0, y: 0 })

let openTimer: ReturnType<typeof setTimeout> | undefined
let closeTimer: ReturnType<typeof setTimeout> | undefined
let warmUntil = 0

function triggerOf(target: EventTarget | null) {
  const el = (target as Element | null)?.closest?.<HTMLElement>('[data-tooltip]')
  return el && root.value?.contains(el) ? el : null
}

async function place(el: HTMLElement) {
  trigger.value?.removeAttribute('aria-describedby')
  trigger.value = el
  text.value = el.dataset.tooltip ?? ''
  kbds.value = el.dataset.tooltipKbds?.split(',').filter(Boolean) ?? []
  el.setAttribute('aria-describedby', id)
  open.value = true

  await nextTick()
  if (!tooltip.value || trigger.value !== el)
    return
  const rect = el.getBoundingClientRect()
  const { width, height } = tooltip.value.getBoundingClientRect()
  const x = Math.min(Math.max(rect.left + rect.width / 2 - width / 2, MARGIN), window.innerWidth - width - MARGIN)
  const below = rect.bottom + OFFSET
  const y = below + height > window.innerHeight - MARGIN ? rect.top - OFFSET - height : below
  position.value = { x, y }
  if (!sliding.value)
    requestAnimationFrame(() => { sliding.value = open.value })
}

function show(el: HTMLElement, immediate = false) {
  clearTimeout(openTimer)
  clearTimeout(closeTimer)
  if (open.value || immediate || Date.now() < warmUntil) {
    place(el)
    return
  }
  openTimer = setTimeout(place, OPEN_DELAY, el)
}

function close() {
  clearTimeout(openTimer)
  clearTimeout(closeTimer)
  if (open.value)
    warmUntil = Date.now() + SKIP_DELAY
  trigger.value?.removeAttribute('aria-describedby')
  trigger.value = null
  open.value = false
  sliding.value = false
}

function hide() {
  clearTimeout(openTimer)
  clearTimeout(closeTimer)
  closeTimer = setTimeout(close, CLOSE_GRACE)
}

function onPointerOver(e: PointerEvent) {
  const el = triggerOf(e.target)
  if (!el)
    return
  if (el !== trigger.value)
    show(el)
  // Back on the control within the grace delay: it stays open instead of closing and coming back
  else
    clearTimeout(closeTimer)
}

function onPointerOut(e: PointerEvent) {
  const from = triggerOf(e.target)
  if (from && from !== triggerOf(e.relatedTarget))
    hide()
}

function onFocusIn(e: FocusEvent) {
  const el = triggerOf(e.target)
  if (el && (e.target as Element).matches(':focus-visible'))
    show(el, true)
}

useEventListener('keydown', (e: KeyboardEvent) => {
  if (e.key === 'Escape' && open.value)
    close()
})

// The tooltip counts as part of its control, so the pointer can go down onto the text without it closing
function onTooltipEnter() {
  clearTimeout(closeTimer)
}

onBeforeUnmount(close)
</script>

<template>
  <div
    ref="root"
    class="contents"
    @pointerover="onPointerOver"
    @pointerout="onPointerOut"
    @pointerdown="close"
    @focusin="onFocusIn"
    @focusout="hide"
  >
    <slot />
  </div>

  <Teleport to="body">
    <Transition
      enter-active-class="animate-[scale-in_100ms_ease-out] motion-reduce:animate-none"
      leave-active-class="pointer-events-none animate-[scale-out_100ms_ease-out_forwards] motion-reduce:animate-none"
    >
      <div
        v-if="open"
        :id="id"
        ref="tooltip"
        role="tooltip"
        class="fixed top-0 left-0 z-[100] flex h-6 origin-top items-center gap-1 rounded-sm before:absolute before:inset-x-0 before:-top-2 before:h-2 after:absolute after:inset-x-0 after:-bottom-2 after:h-2 bg-default px-2.5 py-1 text-xs whitespace-nowrap text-highlighted shadow-sm ring ring-default select-none"
        :class="sliding && 'transition-[translate] duration-150 ease-out motion-reduce:transition-none'"
        :style="{ translate: `${position.x}px ${position.y}px` }"
        @pointerenter="onTooltipEnter"
        @pointerleave="hide"
      >
        <span class="truncate">{{ text }}</span>
        <span v-if="kbds.length" class="hidden shrink-0 items-center gap-0.5 lg:inline-flex">
          <UKbd v-for="kbd in kbds" :key="kbd" :value="kbd" size="sm" />
        </span>
      </div>
    </Transition>
  </Teleport>
</template>
