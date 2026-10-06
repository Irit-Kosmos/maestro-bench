<script setup lang="ts">
import type { StudyDetail, StudyStatus } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// The properties of a study, in the panel on the side of its page: its status and tags are edited in place.
const props = defineProps<{
  study: StudyDetail
}>()

const emit = defineEmits<{
  changed: []
}>()

const { updateStudy } = useStudies()
const { canEdit } = useCurrentWorkspace()
const { formatDate } = useUIHelpers()
const { fail } = useStandardToast()

const meta = computed(() => studyStatusMeta(props.study.status))

async function setStatus(status: StudyStatus) {
  if (status === props.study.status)
    return
  try {
    await updateStudy(props.study.id, { status })
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t change the status', apiErrorMessage(error))
  }
}

const statusItems = computed(() => [STUDY_STATUSES.map(status => ({
  label: status.label,
  icon: status.icon,
  // The icon keeps the colour it has everywhere else
  ui: { itemLeadingIcon: status.tone },
  type: 'checkbox' as const,
  checked: status.value === props.study.status,
  onSelect: () => setStatus(status.value),
}))])

// Every row is one 24px line (the height of the status button): label and value share its centre, and the tags can still wrap below
const rowClass = 'grid grid-cols-[5.5rem_minmax(0,1fr)] items-start gap-2 text-sm leading-6'
const labelClass = 'text-xs leading-6 text-muted'
</script>

<template>
  <aside aria-label="Properties" class="flex flex-col gap-4 text-sm">
    <h2 class="text-xs font-medium text-dimmed">
      Properties
    </h2>

    <div :class="rowClass">
      <span :class="labelClass">Status</span>
      <UDropdownMenu v-if="canEdit" :items="statusItems" size="sm" :content="{ align: 'start' }">
        <UButton color="neutral" variant="ghost" size="xs" class="-ms-2 justify-start" :aria-label="`Status: ${meta.label}`">
          <StudiesStatusIcon :status="study.status" />
          {{ meta.label }}
        </UButton>
      </UDropdownMenu>
      <span v-else class="inline-flex h-6 items-center gap-1.5 text-toned">
        <StudiesStatusIcon :status="study.status" />
        {{ meta.label }}
      </span>
    </div>

    <div :class="rowClass">
      <span :class="labelClass">Tags</span>
      <TagsList :id="study.id" class="min-h-6" :tags="study.tags" :max="20" wrap :kind="canEdit ? 'study' : undefined" @changed="emit('changed')" />
    </div>

    <div :class="rowClass">
      <span :class="labelClass">Items</span>
      <span class="text-toned">{{ describeCounts(study.counts) }}</span>
    </div>

    <div :class="rowClass">
      <span :class="labelClass">Created by</span>
      <span class="inline-flex h-6 min-w-0 items-center gap-1.5 text-toned">
        <UAvatar :src="study.author?.avatar_url ?? undefined" :alt="study.author?.display_name ?? 'Former member'" size="2xs" />
        <span class="truncate">{{ study.author?.display_name ?? 'Former member' }}</span>
      </span>
    </div>

    <div :class="rowClass">
      <span :class="labelClass">Created</span>
      <span class="text-toned">{{ formatDate(study.created_at) }}</span>
    </div>

    <div :class="rowClass">
      <span :class="labelClass">Updated</span>
      <span class="text-toned">{{ formatDate(study.updated_at) }}</span>
    </div>
  </aside>
</template>
