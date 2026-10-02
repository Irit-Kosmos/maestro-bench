<script setup lang="ts">
import type { Tag, TagColor, TagWithCount } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// The tags of an item, by id. The chips are the current tags; the button opens a field that searches the
// shared tags and offers to create one when nothing matches, with the colour to give it.
const selected = defineModel<number[]>({ required: true })

const { tags, refreshTags, createTag } = useTags()
const toast = useToast()

const open = ref(false)
const query = ref('')
const active = ref(0)
// Until one is picked, the colour suggested for a new tag follows what the others use
const pickedColor = ref<TagColor | null>(null)
const creating = ref(false)

const listId = useId()
const optionId = (index: number) => `${listId}-${index}`

const chosen = computed(() => selected.value
  .map(id => tags.value.find(tag => tag.id === id))
  .filter((tag): tag is TagWithCount => !!tag))

const typed = computed(() => normalizeTagName(query.value))
const matches = computed(() => matchTags(tags.value, query.value))
const canCreate = computed(() => !!typed.value && !findTag(tags.value, typed.value))
const color = computed(() => pickedColor.value ?? nextTagColor(tags.value))

type Row = { kind: 'tag', tag: TagWithCount } | { kind: 'create' }

// What the arrow keys walk through: the matches, then the offer to create what was typed
const rows = computed<Row[]>(() => [
  ...matches.value.map((tag): Row => ({ kind: 'tag', tag })),
  ...(canCreate.value ? [{ kind: 'create' } as const] : []),
])

watch(query, () => {
  active.value = 0
})

// Counts change as items are tagged, so the list is read again each time the field opens
watch(open, (isOpen) => {
  if (isOpen) {
    refreshTags()
    return
  }
  query.value = ''
  pickedColor.value = null
})

const isSelected = (tag: Tag) => selected.value.includes(tag.id)

function remove(id: number) {
  selected.value = selected.value.filter(other => other !== id)
}

function toggle(tag: Tag) {
  if (isSelected(tag))
    remove(tag.id)
  else
    selected.value = [...selected.value, tag.id]
  query.value = ''
}

async function create() {
  const name = typed.value
  if (!name || creating.value)
    return
  creating.value = true
  try {
    const tag = await createTag(name, color.value)
    selected.value = [...selected.value, tag.id]
    query.value = ''
    pickedColor.value = null
  }
  catch (error) {
    // Made by someone else in the meantime: that one is the tag
    await refreshTags()
    const existing = findTag(tags.value, name)
    if (existing) {
      if (!isSelected(existing))
        selected.value = [...selected.value, existing.id]
      query.value = ''
    }
    else {
      toast.add({ title: 'Error', description: apiErrorMessage(error) ?? 'Failed to create the tag', color: 'error', icon: 'i-lucide:alert-circle' })
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

const CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <TagsChip
      v-for="tag in chosen"
      :key="tag.id"
      :tag="tag"
      removable
      @remove="remove(tag.id)"
    />

    <UPopover v-model:open="open" :content="CONTENT" :ui="{ content: 'overflow-hidden' }">
      <button
        type="button"
        class="inline-flex h-5 cursor-pointer items-center gap-1 rounded-full border border-dashed border-accented px-2 text-xs text-muted outline-none transition-colors duration-150 hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default data-[state=open]:bg-elevated data-[state=open]:text-default"
        :aria-label="chosen.length ? 'Add a tag' : undefined"
      >
        <UIcon name="i-lucide-plus" class="size-3" aria-hidden="true" />
        <template v-if="!chosen.length">
          Add tags
        </template>
      </button>

      <template #content>
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
                  :class="isSelected(row.tag) ? 'border-inverted bg-inverted text-inverted' : 'border-accented'"
                  aria-hidden="true"
                >
                  <UIcon v-if="isSelected(row.tag)" name="i-lucide-check" class="size-2.5" />
                </span>
                <span class="size-2 shrink-0 rounded-full" :class="tagDot(row.tag.color)" aria-hidden="true" />
                <span class="flex-1 truncate">{{ row.tag.name }}</span>
                <span class="text-xs text-dimmed tabular-nums">{{ row.tag.count }}</span>
              </template>
              <template v-else>
                <UIcon name="i-lucide-plus" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
                <span class="size-2 shrink-0 rounded-full" :class="tagDot(color)" aria-hidden="true" />
                <span class="flex-1 truncate">Create “{{ typed }}”</span>
                <UKbd value="enter" size="sm" />
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
    </UPopover>
  </div>
</template>
