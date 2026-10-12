<script setup lang="ts">
import type { StudyDetail, StudyItem } from '~/types'
import type { FilterSpec } from '~/utils/filters'
import type { GroupSpec } from '~/utils/groups'
import type { SortSpec } from '~/utils/sorts'
import { h, resolveComponent } from 'vue'
import { apiErrorMessage } from '~/composables/useAnalyses'
import { byOrder } from '~/utils/filters'
import { datasetFilter, dateFilter, statusFilter } from '~/utils/filterSpecs'
import { dateSort, figureSort, nameSort, statusSort, textSort } from '~/utils/sortSpecs'

const props = defineProps<{
  study: StudyDetail
}>()

const emit = defineEmits<{
  changed: []
}>()

type Row = StudyItem & { id: string }

const { removeItem } = useStudies()
const { canEdit } = useCurrentWorkspace()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { ok, fail } = useStandardToast()

const writable = computed(() => canEdit.value && props.study.status !== 'archived')

// The table keys its rows by `id`, which no two items of different kinds can share
const rows = computed<Row[]>(() => props.study.items.map(item => ({ ...item, id: `${item.kind}:${item.item_id}` })))

const groupBy = useGroupBy('maestro:study-items-group-by', 'kind')

const UIcon = resolveComponent('UIcon')
const figureClass = 'text-sm text-toned'
const columns = [
  {
    key: 'name',
    label: 'Name',
    formatter: (_: unknown, row: Row) => row.name,
    render: (row: Row) => h('span', { class: 'inline-flex min-w-0 items-center gap-2' }, [
      h(UIcon, { 'name': ITEM_KINDS[row.kind].icon, 'class': 'size-4 shrink-0 text-dimmed', 'aria-hidden': 'true' }),
      h('span', { class: 'truncate font-medium text-highlighted' }, row.name),
    ]),
  },
  { key: 'status', label: 'Status', width: 120 },
  {
    key: 'dataset_name',
    label: 'Dataset',
    width: 160,
    formatter: (_: unknown, row: Row) => row.dataset_name || '—',
  },
  { key: 'execution_count', label: 'Executions', width: 104, class: figureClass, formatter: (count: number) => count ? String(count) : '—' },
  { key: 'total_tokens', label: 'Tokens', width: 80, class: figureClass, formatter: (tokens: number | null) => formatTokens(tokens) },
  { key: 'total_cost_usd', label: 'Cost', width: 88, class: figureClass, formatter: (cost: number | null) => formatCost(cost) },
  { key: 'added_at', label: 'Added', width: 112 },
]

const groups: GroupSpec<Row>[] = [
  {
    key: 'kind',
    label: 'Type',
    icon: 'i-ph-shapes-bold',
    value: row => row.kind,
    present: kind => ({ label: ITEM_KINDS[kind as StudyItem['kind']].plural, icon: ITEM_KINDS[kind as StudyItem['kind']].icon }),
    compare: byOrder(STUDY_KINDS),
  },
]

const filters: FilterSpec<Row>[] = [
  {
    key: 'kind',
    label: 'Type',
    icon: 'i-ph-shapes-bold',
    value: row => row.kind,
    present: kind => ({ label: ITEM_KINDS[kind as StudyItem['kind']].label, icon: ITEM_KINDS[kind as StudyItem['kind']].icon }),
    compare: byOrder(STUDY_KINDS),
  },
  statusFilter<Row>(row => row.status),
  datasetFilter<Row>(row => row.dataset_name),
  dateFilter<Row>(row => row.added_at, 'Added'),
]

const sorts: SortSpec<Row>[] = [
  nameSort<Row>(row => row.name),
  textSort<Row>('kind', 'Type', 'i-ph-shapes-bold', row => ITEM_KINDS[row.kind].label),
  statusSort<Row>(row => row.status),
  figureSort<Row>('executions', 'Executions', 'i-ph-repeat-bold', row => row.execution_count),
  figureSort<Row>('tokens', 'Tokens', 'i-ph-coins-bold', row => row.total_tokens),
  figureSort<Row>('cost', 'Cost', 'i-ph-currency-dollar-bold', row => row.total_cost_usd),
  dateSort<Row>(row => row.added_at, 'Added'),
]

async function remove(items: StudyItem[]) {
  try {
    for (const item of items)
      await removeItem(props.study.id, item.kind, item.item_id)
    ok(items.length === 1 ? 'Removed from the study' : `${items.length} items removed from the study`, { description: 'They were not deleted.' })
  }
  catch (error) {
    fail('Couldn’t remove it from the study', apiErrorMessage(error))
  }
  finally {
    emit('changed')
  }
}

const actions = computed(() => [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (row: Row) => navigateTo(itemPath(row.kind, row.item_id)),
  },
  {
    label: `Remove from ${props.study.name}`,
    icon: 'i-ph-minus-circle-bold',
    requires: 'editor' as const,
    show: () => props.study.status !== 'archived',
    handler: (row: Row) => remove([row]),
  },
])

const selected = ref<(string | number)[]>([])
const selectedRows = computed(() => rows.value.filter(row => selected.value.includes(row.id)))
</script>

<template>
  <BaseDataTable
    v-if="rows.length"
    v-model:selected="selected"
    v-model:group-by="groupBy"
    :data="rows"
    :columns="columns"
    :filters="filters"
    :groups="groups"
    :sorts="sorts"
    :actions="actions"
    :row-to="(row: Row) => itemPath(row.kind, row.item_id)"
    :selectable="writable"
    item-name="item"
    searchable
  >
    <template #selection-actions>
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-minus-circle-bold"
        size="sm"
        @click="remove(selectedRows).then(() => { selected = [] })"
      >
        Remove from {{ study.name }}
      </UButton>
    </template>

    <template #status-cell="{ row }">
      <UIStatusBadge v-if="row.original.status" :status="row.original.status" />
      <span v-else class="text-sm text-dimmed">—</span>
    </template>

    <template #added_at-cell="{ row }">
      <span
        class="text-sm text-muted"
        :title="`${formatDate(row.original.added_at)}${row.original.added_by ? ` by ${row.original.added_by.display_name}` : ''}`"
      >
        {{ formatRelativeDate(row.original.added_at) }}
      </span>
    </template>
  </BaseDataTable>

  <BaseEmptyState
    v-else
    title="Nothing in this study yet"
    message="Select experiments, batches or analyses in their lists and use “Studies” to put them here, or open one and add it from its page."
    icon="i-ph-notebook-bold"
  />
</template>
