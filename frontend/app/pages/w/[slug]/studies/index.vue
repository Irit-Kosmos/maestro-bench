<script setup lang="ts">
import type { Study } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { GroupSpec } from '~/utils/groups'
import type { SortSpec } from '~/utils/sorts'
import { h, resolveComponent } from 'vue'
import { byOrder } from '~/utils/filters'
import { dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'
import { dateSort, figureSort, nameSort, textSort } from '~/utils/sortSpecs'

definePageMeta({
  title: 'Studies',
})

useSeoMeta({
  title: 'Studies',
  description: 'Themes that gather experiments, batches and analyses, with a journal of notes.',
})

const { studies, pending, error, refreshStudies: refresh, deleteStudy } = useStudies()
const { canEdit } = useCurrentWorkspace()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { showDeleteSuccess, showDeleteError } = useStandardToast()

// The studies being worked on come first; how they are cut is remembered per browser
const groupBy = useGroupBy('maestro:studies-group-by', 'status')
const sortBy = useSortBy('maestro:studies-sort-by')

// Studies change from other pages (items added or deleted, notes written): read the list again on arrival
onMounted(() => refresh())

const showCreate = ref(false)
useCreateFromQuery(() => {
  showCreate.value = true
})

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const studyToDelete = ref<Study | null>(null)

const StatusIcon = resolveComponent('StudiesStatusIcon')
const figureClass = 'text-sm text-toned'
const columns = [
  {
    key: 'name',
    label: 'Study',
    formatter: (_: unknown, row: Study) => row.name,
    render: (row: Study) => h('span', { class: 'inline-flex min-w-0 items-center gap-2' }, [
      h(StatusIcon, { status: row.status }),
      h('span', { class: 'truncate font-medium text-highlighted' }, row.name),
    ]),
  },
  {
    key: 'tags',
    label: 'Tags',
    width: 220,
    // What the search reads; the cell below shows the chips
    formatter: (_: unknown, row: Study) => row.tags.map(tag => tag.name).join(' '),
  },
  {
    key: 'counts',
    label: 'Items',
    width: 240,
    formatter: (_: unknown, row: Study) => describeCounts(row.counts),
  },
  { key: 'execution_count', label: 'Executions', width: 104, class: figureClass, formatter: (count: number) => count ? String(count) : '—' },
  { key: 'total_tokens', label: 'Tokens', width: 80, class: figureClass, formatter: (tokens: number | null) => formatTokens(tokens) },
  { key: 'total_cost_usd', label: 'Cost', width: 88, class: figureClass, formatter: (cost: number | null) => formatCost(cost) },
  { key: 'updated_at', label: 'Updated', width: 112 },
]

function presentStatus(status: string | number | boolean) {
  const meta = studyStatusMeta(String(status))
  return { label: meta.label, icon: meta.icon, iconClass: meta.tone }
}

const groups: GroupSpec<Study>[] = [
  {
    key: 'status',
    label: 'Status',
    icon: 'i-ph-circle-half-bold',
    value: study => study.status,
    present: presentStatus,
    compare: byOrder(STUDY_STATUS_ORDER),
  },
]

const filters: FilterSpec<Study>[] = [
  {
    key: 'status',
    label: 'Status',
    icon: 'i-ph-circle-half-bold',
    value: study => study.status,
    present: presentStatus,
    compare: byOrder(STUDY_STATUS_ORDER),
  },
  tagsFilter<Study>(study => study.tags),
  dateFilter<Study>(study => study.updated_at, 'Updated'),
]

// In the order of the columns
const sorts: SortSpec<Study>[] = [
  nameSort<Study>(study => study.name, 'Study'),
  textSort<Study>('status', 'Status', 'i-ph-circle-half-bold', study => studyStatusMeta(study.status).label),
  figureSort<Study>('items', 'Items', 'i-ph-stack-bold', study => itemCount(study.counts)),
  figureSort<Study>('executions', 'Executions', 'i-ph-repeat-bold', study => study.execution_count),
  figureSort<Study>('tokens', 'Tokens', 'i-ph-coins-bold', study => study.total_tokens),
  figureSort<Study>('cost', 'Cost', 'i-ph-currency-dollar-bold', study => study.total_cost_usd),
  dateSort<Study>(study => study.updated_at, 'Updated'),
]

// Clicking a tag in a row filters the list on it
const filterState = ref<FilterState>({})

const actions = [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (study: Study) => navigateTo(`/studies/${study.id}`),
  },
  {
    label: 'Delete',
    icon: 'i-ph-trash-bold',
    variant: 'ghost' as const,
    color: 'error' as const,
    requires: 'editor' as const,
    handler: (study: Study) => {
      studyToDelete.value = study
      showDeleteDialog.value = true
    },
  },
]

async function confirmDelete() {
  if (!studyToDelete.value)
    return
  isDeleting.value = true
  try {
    await deleteStudy(studyToDelete.value.id)
    showDeleteSuccess('Study')
    showDeleteDialog.value = false
    studyToDelete.value = null
  }
  catch {
    showDeleteError('Study')
  }
  finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <BasePageContent
    :loading="pending && !studies.length"
    :error="!studies.length && !!error"
    :error-kind="fetchErrorKind(error)"
    @retry="refresh()"
  >
    <template #before-content>
      <UTooltip text="New study" :kbds="['C']" :disabled="!canEdit">
        <UIGuardedButton
          color="neutral"
          variant="soft"
          icon="i-ph-plus-bold"
          size="sm"
          @click="showCreate = true"
        >
          New study
        </UIGuardedButton>
      </UTooltip>
    </template>

    <div v-if="studies.length > 0">
      <BaseDataTable
        v-model:filter-state="filterState"
        v-model:group-by="groupBy"
        v-model:sort-by="sortBy"
        :data="[...studies]"
        :columns="columns"
        :filters="filters"
        :groups="groups"
        :sorts="sorts"
        :actions="actions"
        :loading="pending"
        :row-to="(study: Study) => `/studies/${study.id}`"
        :row-hint="(study: Study) => `#${study.id}`"
        item-name="study"
        item-name-plural="studies"
        searchable
        @refresh="refresh"
      >
        <template #tags-cell="{ row }">
          <TagsList
            :id="row.original.id"
            :tags="row.original.tags"
            :kind="canEdit ? 'study' : undefined"
            selectable
            @changed="refresh"
            @select="tag => { filterState = filterByTag(filterState, tag.name) }"
          />
        </template>

        <template #updated_at-cell="{ row }">
          <span class="text-sm text-muted" :title="formatDate(row.original.updated_at)">
            {{ formatRelativeDate(row.original.updated_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <BaseEmptyState
      v-else-if="!pending"
      title="No studies yet"
      message="A study gathers the experiments, batches and analyses around one question, and keeps your notes about what they show."
      icon="i-ph-notebook-bold"
      action-label="New study"
      action-requires="editor"
      @action="showCreate = true"
    />

    <StudiesCreateModal v-model:open="showCreate" @created="study => navigateTo(`/studies/${study.id}`)" />

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete study?"
      message="Its notes are deleted with it. The experiments, batches and analyses it gathers are kept."
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="confirmDelete"
    />
  </BasePageContent>
</template>
