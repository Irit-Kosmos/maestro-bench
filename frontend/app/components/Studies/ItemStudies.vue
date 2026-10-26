<script setup lang="ts">
import type { Study, StudyKind } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  kind: StudyKind
  id: number
}>()

const { studies, assignStudies } = useStudies()
const { fail } = useStandardToast()
const { memberships, refreshMemberships } = useStudyMemberships(() => props.kind)
const { canEdit } = useCurrentWorkspace()

const mine = computed(() => {
  const ids = new Set(memberships.value.filter(m => m.item_id === props.id).map(m => m.study_id))
  return studies.value.filter(study => ids.has(study.id))
})

async function remove(study: Study) {
  try {
    await assignStudies(props.kind, [props.id], { remove: [study.id] })
    await refreshMemberships()
  }
  catch (error) {
    fail('Couldn’t remove from the study', apiErrorMessage(error))
  }
}
</script>

<template>
  <div v-if="mine.length || canEdit" class="flex flex-wrap items-center gap-1.5">
    <span
      v-for="study in mine"
      :key="study.id"
      class="inline-flex h-6 max-w-56 items-center rounded-md border border-default text-xs text-toned transition-colors hover:bg-elevated"
    >
      <NuxtLink
        :to="`/studies/${study.id}`"
        class="inline-flex min-w-0 items-center gap-1.5 rounded-s-md ps-2 text-toned outline-none transition-colors hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
        :class="canEdit ? 'pe-1' : 'rounded-e-md pe-2'"
      >
        <StudiesStatusIcon :status="study.status" />
        <span class="truncate">{{ study.name }}</span>
      </NuxtLink>
      <button
        v-if="canEdit"
        type="button"
        class="me-0.5 inline-flex size-5 shrink-0 cursor-pointer items-center justify-center rounded text-muted outline-none transition-colors hover:bg-accented hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
        :aria-label="`Remove from ${study.name}`"
        data-tooltip="Remove from this study"
        @click="remove(study)"
      >
        <UIcon name="i-ph-x-bold" class="size-3" aria-hidden="true" />
      </button>
    </span>

    <StudiesBulkMenu v-if="canEdit" :kind="kind" :ids="[id]" @changed="refreshMemberships">
      <button
        type="button"
        class="inline-flex h-6 cursor-pointer items-center gap-1 rounded-md border border-dashed border-accented px-2 text-xs text-muted outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default focus-visible:ring-2 focus-visible:ring-inverted data-[state=open]:bg-elevated data-[state=open]:text-default"
      >
        <UIcon name="i-ph-plus-bold" class="size-3" aria-hidden="true" />
        {{ mine.length ? 'Add to another study' : 'Add to a study' }}
      </button>
    </StudiesBulkMenu>
  </div>
</template>
