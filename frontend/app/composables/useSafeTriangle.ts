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
