<script setup lang="ts">
import type { PlaceholderSegment } from '~/utils/promptPlaceholders'

const props = withDefaults(defineProps<{
  /** Declared variable names */
  variables: readonly string[]
  /** Variable being looked at elsewhere (a chip under hover), shown stronger */
  active?: string | null
  rows?: number
  placeholder?: string
}>(), {
  active: null,
  rows: 4,
})

const text = defineModel<string>({ required: true })

const { id, disabled } = useFormField()

const field = useTemplateRef<HTMLTextAreaElement>('field')
const backdrop = useTemplateRef<HTMLElement>('backdrop')
// Set from inside the backdrop's v-for, where a template ref would be a list
let anchor: HTMLElement | null = null
function setAnchor(el: unknown) {
  anchor = el as HTMLElement | null
}

// What the completion would replace: from the `{{` to the caret, and the typed name so far
interface Completion {
  from: number
  caret: number
  query: string
}
const completion = ref<Completion | null>(null)
const selected = ref(0)
const popup = ref<{ left: number, top: number } | null>(null)

const candidates = computed(() => {
  const open = completion.value
  if (!open)
    return []
  const query = open.query.toLowerCase()
  const names = props.variables.filter(name => name.toLowerCase().startsWith(query))
  // Nothing left to offer once the name is typed in full
  return names.length === 1 && names[0] === open.query ? [] : names
})
const isOpen = computed(() => candidates.value.length > 0)

// The backdrop is the text cut into plain runs and placeholders. While the completion is open it is also cut at the
// caret, where a zero-width anchor lets the list sit under the caret.
type Piece = PlaceholderSegment | { anchor: true }
const pieces = computed<Piece[]>(() => {
  const caret = completion.value?.caret
  const out: Piece[] = []
  let offset = 0
  let anchored = caret === undefined
  for (const segment of splitPlaceholders(text.value, props.variables)) {
    const end = offset + segment.text.length
    if (!anchored && caret! >= offset && caret! <= end) {
      const cut = caret! - offset
      if (cut > 0)
        out.push({ ...segment, text: segment.text.slice(0, cut) })
      out.push({ anchor: true })
      if (cut < segment.text.length)
        out.push({ ...segment, text: segment.text.slice(cut) })
      anchored = true
    }
    else {
      out.push(segment)
    }
    offset = end
  }
  if (!anchored)
    out.push({ anchor: true })
  return out
})

function markClass(placeholder: NonNullable<PlaceholderSegment['placeholder']>) {
  if (!placeholder.declared)
    return 'bg-warning/15 underline decoration-warning decoration-wavy underline-offset-2'
  return placeholder.name === props.active ? 'bg-primary/25' : 'bg-primary/10'
}

function refreshCompletion(reset = false) {
  const el = field.value
  if (!el || props.variables.length === 0 || el.selectionStart !== el.selectionEnd) {
    completion.value = null
    return
  }
  const caret = el.selectionStart
  // The textarea's own value: the model only catches up once the parent has rendered
  const typed = /\{\{-?[ \t]*([A-Z_]\w*)?$/i.exec(el.value.slice(0, caret))
  if (!typed) {
    completion.value = null
    return
  }
  completion.value = { from: caret - typed[0].length, caret, query: typed[1] ?? '' }
  if (reset)
    selected.value = 0
  selected.value = Math.min(selected.value, Math.max(candidates.value.length - 1, 0))
}

// Under the caret, in the field's own box: read once the anchor is in the DOM
watch([isOpen, completion], async () => {
  if (!isOpen.value) {
    popup.value = null
    return
  }
  await nextTick()
  if (anchor)
    popup.value = { left: anchor.offsetLeft, top: anchor.offsetTop + anchor.offsetHeight }
})

function onInput(event: Event) {
  text.value = (event.target as HTMLTextAreaElement).value
  refreshCompletion(true)
}

function accept(name: string) {
  const el = field.value
  const open = completion.value
  if (!el || !open)
    return
  // Take the closing braces already there, so completing inside `{{ }}` does not double them
  const closing = /^[ \t]*\}\}/.exec(el.value.slice(open.caret))
  el.focus()
  el.setSelectionRange(open.from, open.caret + (closing?.[0].length ?? 0))
  // insertText keeps the browser's undo history; the fallback is for when it is not available
  if (!document.execCommand('insertText', false, `{{ ${name} }}`)) {
    const end = open.caret + (closing?.[0].length ?? 0)
    text.value = `${el.value.slice(0, open.from)}{{ ${name} }}${el.value.slice(end)}`
  }
  completion.value = null
}

function onKeydown(event: KeyboardEvent) {
  if (!isOpen.value)
    return
  const count = candidates.value.length
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    selected.value = (selected.value + (event.key === 'ArrowDown' ? 1 : count - 1)) % count
  }
  else if ((event.key === 'Enter' || event.key === 'Tab') && !event.metaKey && !event.ctrlKey && !event.shiftKey) {
    event.preventDefault()
    event.stopPropagation()
    accept(candidates.value[selected.value]!)
  }
  else if (event.key === 'Escape') {
    // Closes the list only: the form's own Esc (cancel) must not fire
    event.stopPropagation()
    completion.value = null
  }
}

function onKeyup(event: KeyboardEvent) {
  if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key))
    refreshCompletion()
}

/** Select a range and bring it into view (the field never scrolls: the pane around it does) */
function select(start: number, end: number) {
  const el = field.value
  if (!el)
    return
  el.focus({ preventScroll: true })
  el.setSelectionRange(start, end)
  backdrop.value?.querySelector(`[data-start="${start}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

defineExpose({ select })

// Same box as the textarea, so that the two wrap alike
const box = 'px-2.5 py-1.5 font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-words'
</script>

<template>
  <div class="relative rounded-md bg-default ring ring-inset ring-accented focus-within:ring-2 focus-within:ring-inverted">
    <div
      ref="backdrop"
      aria-hidden="true"
      :class="box"
      class="pointer-events-none select-none text-transparent"
      :style="{ minHeight: `calc(${rows}lh + 0.75rem)` }"
    >
      <template v-for="(piece, index) in pieces" :key="index">
        <span v-if="'anchor' in piece" :ref="setAnchor" class="inline-block h-[1lh] w-0 align-top" />
        <mark
          v-else-if="piece.placeholder"
          :data-start="piece.placeholder.start"
          class="rounded-sm text-transparent transition-colors duration-100"
          :class="markClass(piece.placeholder)"
        >{{ piece.text }}</mark>
        <span v-else>{{ piece.text }}</span>
      </template>
      <!-- A trailing newline would not make a line of its own without something after it -->
      &#8203;
    </div>

    <textarea
      :id="id"
      ref="field"
      :value="text"
      :placeholder="placeholder"
      :disabled="disabled"
      :class="box"
      class="absolute inset-0 size-full resize-none overflow-hidden rounded-md bg-transparent text-highlighted outline-none placeholder:text-dimmed disabled:cursor-not-allowed disabled:opacity-75"
      spellcheck="false"
      aria-autocomplete="list"
      @input="onInput"
      @keydown="onKeydown"
      @keyup="onKeyup"
      @click="refreshCompletion()"
      @blur="completion = null"
    />

    <ul
      v-if="isOpen && popup"
      role="listbox"
      class="absolute z-10 mt-0.5 min-w-40 max-w-72 overflow-hidden rounded-md bg-default p-1 shadow-lg ring ring-default"
      :style="{ left: `${popup.left}px`, top: `${popup.top}px` }"
    >
      <li
        v-for="(name, index) in candidates"
        :key="name"
        role="option"
        :aria-selected="index === selected"
        class="cursor-default truncate rounded-sm px-2 py-1 font-mono text-xs text-highlighted"
        :class="index === selected ? 'bg-elevated' : ''"
        @mousedown.prevent="accept(name)"
        @mousemove="selected = index"
      >
        {{ name }}
      </li>
    </ul>
  </div>
</template>
