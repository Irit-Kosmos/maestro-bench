<script setup lang="ts">
import type { Study } from '~/types'

const props = withDefaults(defineProps<{
  /** Studies every target is in */
  selected: number[]
  /** Studies only part of the targets are in: shown as a dash, for several items at once */
  partial?: number[]
  /** A study is being made from what was typed */
  creating?: boolean
  /** Only offers the studies still running (and the ones already chosen), for work that is about to start */
  activeOnly?: boolean
}>(), {
  partial: () => [],
  creating: false,
  activeOnly: false,
})

const emit = defineEmits<{
  /** A study of the list was clicked or chosen with ↵ */
  toggle: [study: Study]
  /** The offer to create a study from what was typed was taken */
  create: [name: string]
}>()

const { studies, refreshStudies } = useStudies()

// Read again each time the popover opens, in case studies were made or renamed elsewhere
onMounted(refreshStudies)

const query = ref('')
const active = ref(0)

const listId = useId()
const optionId = (index: number) => `${listId}-${index}`

const typed = computed(() => query.value.trim().split(/\s+/).filter(Boolean).join(' '))
const offered = computed(() => studies.value.filter(study => props.activeOnly
  ? study.status === 'active' || props.selected.includes(study.id)
  : study.status !== 'archived'))
const matches = computed(() => matchStudies(offered.value, query.value))
const canCreate = computed(() => !!typed.value && !findStudy(studies.value, typed.value))

type Row = { kind: 'study', study: Study } | { kind: 'create' }

// What the arrow keys walk through: the matches, then the offer to create what was typed
const rows = computed<Row[]>(() => [
  ...matches.value.map((study): Row => ({ kind: 'study', study })),
  ...(canCreate.value ? [{ kind: 'create' } as const] : []),
])

watch(query, () => {
  active.value = 0
})

const isSelected = (study: Study) => props.selected.includes(study.id)
const isPartial = (study: Study) => !isSelected(study) && props.partial.includes(study.id)

function activate(row: Row | undefined) {
  if (!row)
    return
  if (row.kind === 'study') {
    emit('toggle', row.study)
    query.value = ''
  }
  else if (!props.creating) {
    emit('create', typed.value)
    query.value = ''
  }
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
  <div class="flex w-72 flex-col">
    <input
      v-model="query"
      type="text"
      role="combobox"
      aria-expanded="true"
      aria-autocomplete="list"
      :aria-controls="listId"
      :aria-activedescendant="rows.length ? optionId(active) : undefined"
      placeholder="Search or create a study…"
      aria-label="Search or create a study"
      autocomplete="off"
      maxlength="200"
      class="h-8 w-full shrink-0 rounded-t-[calc(var(--radius-md)-1px)] border-0 border-b border-default bg-transparent px-2.5 text-xs text-highlighted outline-none placeholder:text-dimmed focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
      @keydown="onKeydown"
    >

    <div
      :id="listId"
      ref="list"
      role="listbox"
      aria-label="Studies"
      aria-multiselectable="true"
      class="flex max-h-56 min-h-0 flex-col overflow-y-auto p-1"
    >
      <div
        v-for="(row, index) in rows"
        :id="optionId(index)"
        :key="row.kind === 'study' ? row.study.id : 'create'"
        role="option"
        :aria-selected="row.kind === 'study' ? isSelected(row.study) : false"
        :data-active="index === active"
        class="flex h-7 shrink-0 cursor-pointer items-center gap-2 rounded-sm px-1.5 text-xs text-default"
        :class="index === active ? 'bg-elevated' : undefined"
        @mousedown.prevent
        @pointermove="active = index"
        @click="activate(row)"
      >
        <template v-if="row.kind === 'study'">
          <span
            class="flex size-3.5 shrink-0 items-center justify-center rounded-xs border"
            :class="isSelected(row.study) || isPartial(row.study) ? 'border-inverted bg-inverted text-inverted' : 'border-accented'"
            aria-hidden="true"
          >
            <UIcon v-if="isSelected(row.study)" name="i-ph-check-bold" class="size-2.5" />
            <UIcon v-else-if="isPartial(row.study)" name="i-ph-minus-bold" class="size-2.5" />
          </span>
          <StudiesStatusIcon :status="row.study.status" />
          <span class="flex-1 truncate">{{ row.study.name }}</span>
          <span v-if="isPartial(row.study)" class="sr-only">(for some of the selected rows)</span>
        </template>
        <template v-else>
          <UIcon name="i-ph-plus-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
          <span class="flex-1 truncate">Create “{{ typed }}”</span>
          <BaseKbd value="enter" />
        </template>
      </div>
      <span v-if="!rows.length" class="px-1.5 py-2 text-xs text-muted">No studies yet. Type a name to create one.</span>
    </div>
  </div>
</template>
