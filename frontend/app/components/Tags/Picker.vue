<script setup lang="ts">
import type { Tag, TagColor } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// What a tag popover holds: a field that searches the shared tags and offers to create one when nothing
// matches, with the colour to give it. It only reports what was picked; the caller decides what that does
// (TagsInput sets the tags of one item, TagsBulkMenu those of several).
const props = withDefaults(defineProps<{
  /** Tags the target has */
  selected: number[]
  /** Tags only part of the targets have: shown as a dash, for several items at once */
  partial?: number[]
}>(), {
  partial: () => [],
})

const emit = defineEmits<{
  /** A tag of the list was clicked or chosen with ↵ */
  toggle: [tag: Tag]
  /** A new tag was made from what was typed */
  create: [tag: Tag]
}>()

const { tags, refreshTags, createTag } = useTags()
const { fail } = useStandardToast()

// The list is read again each time the popover opens, in case tags were made or renamed elsewhere
onMounted(refreshTags)

const query = ref('')
const active = ref(0)
// Until one is picked, the colour suggested for a new tag follows what the others use
const pickedColor = ref<TagColor | null>(null)
const creating = ref(false)

const listId = useId()
const optionId = (index: number) => `${listId}-${index}`

const typed = computed(() => normalizeTagName(query.value))
const matches = computed(() => matchTags(tags.value, query.value))
const canCreate = computed(() => !!typed.value && !findTag(tags.value, typed.value))
const color = computed(() => pickedColor.value ?? nextTagColor(tags.value))

type Row = { kind: 'tag', tag: Tag } | { kind: 'create' }

// What the arrow keys walk through: the matches, then the offer to create what was typed
const rows = computed<Row[]>(() => [
  ...matches.value.map((tag): Row => ({ kind: 'tag', tag })),
  ...(canCreate.value ? [{ kind: 'create' } as const] : []),
])

watch(query, () => {
  active.value = 0
})

const isSelected = (tag: Tag) => props.selected.includes(tag.id)
const isPartial = (tag: Tag) => !isSelected(tag) && props.partial.includes(tag.id)

function toggle(tag: Tag) {
  emit('toggle', tag)
  query.value = ''
}

async function create() {
  const name = typed.value
  if (!name || creating.value)
    return
  creating.value = true
  try {
    emit('create', await createTag(name, color.value))
    query.value = ''
    pickedColor.value = null
  }
  catch (error) {
    // Made by someone else in the meantime: that one is the tag
    await refreshTags()
    const existing = findTag(tags.value, name)
    if (existing) {
      emit('create', existing)
      query.value = ''
    }
    else {
      fail('Couldn’t create the tag', apiErrorMessage(error))
    }
  }
  finally {
    creating.value = false
  }
}

function activate(row: Row | undefined) {
  if (!row)
    return
  if (row.kind === 'tag')
    toggle(row.tag)
  else
    create()
}

const list = useTemplateRef<HTMLElement>('list')

function move(direction: 1 | -1) {
  const count = rows.value.length
  if (!count)
    return
  active.value = (active.value + direction + count) % count
  nextTick(() => list.value?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' }))
}

function onKeydown(event: KeyboardEvent) {
  if (event.isComposing)
    return
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    move(1)
  }
  else if (event.key === 'ArrowUp') {
    event.preventDefault()
    move(-1)
  }
  else if (event.key === 'Enter') {
    // Never submits the form the field sits in
    event.preventDefault()
    activate(rows.value[active.value])
  }
}
</script>

<template>
  <div class="flex w-64 flex-col">
    <input
      v-model="query"
      type="text"
      role="combobox"
      aria-expanded="true"
      aria-autocomplete="list"
      :aria-controls="listId"
      :aria-activedescendant="rows.length ? optionId(active) : undefined"
      placeholder="Search or create a tag…"
      aria-label="Search or create a tag"
      autocomplete="off"
      maxlength="40"
      class="h-8 w-full shrink-0 border-0 border-b border-default bg-transparent px-2.5 text-xs text-highlighted outline-none placeholder:text-dimmed"
      @keydown="onKeydown"
    >

    <div
      :id="listId"
      ref="list"
      role="listbox"
      aria-label="Tags"
      aria-multiselectable="true"
      class="flex max-h-56 min-h-0 flex-col overflow-y-auto p-1"
    >
      <div
        v-for="(row, index) in rows"
        :id="optionId(index)"
        :key="row.kind === 'tag' ? row.tag.id : 'create'"
        role="option"
        :aria-selected="row.kind === 'tag' ? isSelected(row.tag) : false"
        :data-active="index === active"
        class="flex h-7 shrink-0 cursor-pointer items-center gap-2 rounded-sm px-1.5 text-xs text-default"
        :class="index === active ? 'bg-elevated' : undefined"
        @mousedown.prevent
        @pointermove="active = index"
        @click="activate(row)"
      >
        <template v-if="row.kind === 'tag'">
          <span
            class="flex size-3.5 shrink-0 items-center justify-center rounded-xs border"
            :class="isSelected(row.tag) || isPartial(row.tag) ? 'border-inverted bg-inverted text-inverted' : 'border-accented'"
            aria-hidden="true"
          >
            <UIcon v-if="isSelected(row.tag)" name="i-ph-check-bold" class="size-2.5" />
            <UIcon v-else-if="isPartial(row.tag)" name="i-ph-minus-bold" class="size-2.5" />
          </span>
          <span class="size-2 shrink-0 rounded-full" :class="tagDot(row.tag.color)" aria-hidden="true" />
          <span class="flex-1 truncate">{{ row.tag.name }}</span>
          <span v-if="isPartial(row.tag)" class="sr-only">(on some of the selected rows)</span>
        </template>
        <template v-else>
          <UIcon name="i-ph-plus-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
          <span class="size-2 shrink-0 rounded-full" :class="tagDot(color)" aria-hidden="true" />
          <span class="flex-1 truncate">Create “{{ typed }}”</span>
          <BaseKbd value="enter" />
        </template>
      </div>
      <span v-if="!rows.length" class="px-1.5 py-2 text-xs text-muted">No tags yet. Type a name to create one.</span>
    </div>

    <!-- The colour of the tag about to be created -->
    <div
      v-if="canCreate"
      role="radiogroup"
      aria-label="Tag colour"
      class="flex items-center justify-between border-t border-default px-2.5 py-2"
    >
      <button
        v-for="option in TAG_COLORS"
        :key="option"
        type="button"
        role="radio"
        :aria-checked="option === color"
        :aria-label="option"
        :title="option"
        class="size-4 shrink-0 cursor-pointer rounded-full outline-none transition-shadow duration-150 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-(--ui-text-highlighted) focus-visible:ring-offset-(--ui-bg)"
        :class="[tagDot(option), option === color ? 'ring-2 ring-offset-2 ring-(--ui-text-highlighted) ring-offset-(--ui-bg)' : undefined]"
        @mousedown.prevent
        @click="pickedColor = option"
      />
    </div>
  </div>
</template>
