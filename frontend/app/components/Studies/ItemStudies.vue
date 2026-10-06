<script setup lang="ts">
import type { StudyKind } from '~/types'

const props = defineProps<{
  kind: StudyKind
  id: number
}>()

const { studies } = useStudies()
const { memberships, refreshMemberships } = useStudyMemberships(() => props.kind)
const { canEdit } = useCurrentWorkspace()

const mine = computed(() => {
  const ids = new Set(memberships.value.filter(m => m.item_id === props.id).map(m => m.study_id))
  return studies.value.filter(study => ids.has(study.id))
})
</script>

<template>
  <div v-if="mine.length || canEdit" class="flex flex-wrap items-center gap-1.5">
    <NuxtLink
      v-for="study in mine"
      :key="study.id"
      :to="`/studies/${study.id}`"
      class="inline-flex h-6 max-w-56 items-center gap-1.5 rounded-md border border-default px-2 text-xs text-toned outline-none transition-colors hover:bg-elevated hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
    >
      <StudiesStatusIcon :status="study.status" />
      <span class="truncate">{{ study.name }}</span>
    </NuxtLink>

    <StudiesBulkMenu v-if="canEdit" :kind="kind" :ids="[id]" @changed="refreshMemberships">
      <button
        type="button"
        class="inline-flex h-6 cursor-pointer items-center gap-1 rounded-md border border-dashed border-accented px-2 text-xs text-muted outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default data-[state=open]:bg-elevated data-[state=open]:text-default"
      >
        <UIcon name="i-ph-plus-bold" class="size-3" aria-hidden="true" />
        {{ mine.length ? 'Study' : 'Add to a study' }}
      </button>
    </StudiesBulkMenu>
  </div>
</template>
