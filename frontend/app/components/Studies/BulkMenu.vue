<script setup lang="ts">
import type { Study, StudyKind } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  kind: StudyKind
  /** Ids of the selected items */
  ids: number[]
}>()

const emit = defineEmits<{
  /** The studies of the items changed */
  changed: []
}>()

const { createStudy, assignStudies, refreshStudies } = useStudies()
const { memberships, refreshMemberships } = useStudyMemberships(() => props.kind)
const { ok, fail } = useStandardToast()

const coverage = computed(() => studyCoverage(memberships.value, props.ids))
function studyIds(everyItem: boolean) {
  return [...coverage.value]
    .filter(([, count]) => everyItem ? count === props.ids.length : count < props.ids.length)
    .map(([id]) => id)
}
const onEvery = computed(() => studyIds(true))
const onSome = computed(() => studyIds(false))

const creating = ref(false)

async function apply(change: { add?: number[], remove?: number[] }) {
  try {
    await assignStudies(props.kind, props.ids, change)
    await refreshMemberships()
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t update the studies', apiErrorMessage(error))
  }
}

function toggle(study: Study) {
  return apply(onEvery.value.includes(study.id) ? { remove: [study.id] } : { add: [study.id] })
}

// A study made here starts with the selection in it
async function create(name: string) {
  creating.value = true
  try {
    const study = await createStudy({ name, items: props.ids.map(item_id => ({ kind: props.kind, item_id })) })
    await refreshMemberships()
    ok('Study created', { description: `“${study.name}” holds the selection.`, action: { label: 'Open', to: `/studies/${study.id}` } })
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t create the study', apiErrorMessage(error))
  }
  finally {
    creating.value = false
  }
}

function onOpen(open: boolean) {
  if (open) {
    refreshStudies()
    refreshMemberships()
  }
}

const CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
</script>

<template>
  <UPopover :content="CONTENT" :ui="{ content: 'overflow-hidden' }" @update:open="onOpen">
    <slot>
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-notebook-bold"
        size="sm"
      >
        Studies
      </UButton>
    </slot>

    <template #content>
      <StudiesPicker
        :selected="onEvery"
        :partial="onSome"
        :creating="creating"
        @toggle="toggle"
        @create="create"
      />
    </template>
  </UPopover>
</template>
