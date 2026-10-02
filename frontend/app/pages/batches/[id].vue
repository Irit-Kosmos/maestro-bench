<script setup lang="ts">
import type { Batch, Model } from '~/types'

const route = useRoute()
const batchId = computed(() => Number.parseInt(route.params.id as string))

const toast = useToast()
const { cancelBatch, deleteBatch } = useBatches()
const { formatDate, formatDuration } = useUIHelpers()

const { data: batch, pending, error, refresh } = await useMyLazyFetch<Batch>(() => `/batches/${batchId.value}`)

// Model values only carry an id and a name: the catalogue says whose they are
const { data: models } = await useMyLazyFetch<Model[]>('/models')
const modelsById = computed(() => new Map((models.value ?? []).map(m => [m.id, m])))

useBreadcrumbLabel(() => batch.value?.name)
useSeoMeta({ title: () => batch.value?.name ?? 'Batch' })

const isActive = computed(() => batch.value?.status === 'running' || batch.value?.status === 'pending')

// The experiments run in the background: follow them until they are all done
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => {
    if (isActive.value)
      refresh()
  }, 4000)
})
onBeforeUnmount(() => clearInterval(timer))

// One column per varied field, named after the agent too when several agents are involved
const multipleAgents = computed(() => new Set(batch.value?.variations.map(v => v.agent_id)).size > 1)
const fieldNames: Record<string, string> = {
  model_id: 'Model',
  prompt_version_id: 'Prompt version',
  temperature: 'Temperature',
}
const axes = computed(() => (batch.value?.variations ?? []).map(v => ({
  key: `${v.agent_id}:${v.field}`,
  agent_id: v.agent_id,
  field: v.field,
  title: multipleAgents.value ? `${v.agent_name} · ${fieldNames[v.field]}` : fieldNames[v.field],
  values: v.values.map(value => value.label),
  // Models read better under their provider: a comparison across providers is the point of most batches
  providerGroups: v.field === 'model_id' ? groupByProvider(v.values) : [],
})))

function groupByProvider(values: Batch['variations'][number]['values']) {
  const groups = new Map<string, string[]>()
  for (const { value, label } of values) {
    const provider = (value === null ? undefined : modelsById.value.get(value)?.provider) ?? ''
    const key = provider ? providerMeta(provider).key : ''
    groups.set(key, [...(groups.get(key) ?? []), label])
  }
  return [...groups.keys()]
    .sort((a, b) => (a && b) ? compareProviders(a, b) : Number(!a) - Number(!b))
    .map(key => ({ key, label: key ? providerLabel(key) : '', names: groups.get(key)! }))
}

function labelOf(experiment: Batch['experiments'][number], axis: { agent_id: number, field: string }) {
  return experiment.coordinates.find(c => c.agent_id === axis.agent_id && c.field === axis.field)?.label ?? '—'
}

// The provider of the model an experiment ran on this axis, once the catalogue has loaded
function providerOf(experiment: Batch['experiments'][number], axis: { agent_id: number, field: string }) {
  if (axis.field !== 'model_id')
    return undefined
  const value = experiment.coordinates.find(c => c.agent_id === axis.agent_id && c.field === axis.field)?.value
  return typeof value === 'number' ? modelsById.value.get(value)?.provider : undefined
}

const finished = computed(() => (batch.value?.experiments ?? []).filter(e => e.status === 'completed').length)

const completed = computed(() => (batch.value?.experiments ?? []).filter(e => e.status === 'completed' && e.execution_id))
const analyzeLink = computed(() => completed.value.length > 0
  ? { path: '/analyses/new', query: { executions: completed.value.map(e => e.execution_id).join(','), name: batch.value?.name } }
  : undefined)

// --- Actions ---

const isCancelling = ref(false)
async function handleCancel() {
  isCancelling.value = true
  const result = await cancelBatch(batchId.value)
  isCancelling.value = false
  if (result.success) {
    toast.add({ title: 'Batch cancelled', description: `${result.data.cancelled} running experiments stopped.`, color: 'success', icon: 'i-lucide:check-circle' })
    await refresh()
  }
  else {
    toast.add({ title: 'Error', description: 'Failed to cancel the batch', color: 'error', icon: 'i-lucide:alert-circle' })
  }
}

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
async function handleDelete() {
  isDeleting.value = true
  const result = await deleteBatch(batchId.value)
  isDeleting.value = false
  showDeleteDialog.value = false
  if (result.success) {
    toast.add({ title: 'Batch deleted', description: 'Its experiments were kept.', color: 'success', icon: 'i-lucide:check-circle' })
    await navigateTo('/batches')
  }
  else {
    toast.add({ title: 'Error', description: 'Failed to delete the batch', color: 'error', icon: 'i-lucide:alert-circle' })
  }
}

function formatCost(cost: number | null) {
  return cost === null ? '—' : `$${cost.toFixed(4)}`
}
</script>

<template>
  <div class="pb-6">
    <BaseLoadingState v-if="pending && !batch" />
    <BaseErrorState v-else-if="error && !batch" message="This batch could not be loaded." />

    <div v-else-if="batch" class="mx-auto flex max-w-6xl flex-col gap-8">
      <AppPageActions>
        <UButton
          v-if="isActive"
          variant="outline"
          color="neutral"
          icon="i-lucide-circle-stop"
          size="sm"
          :loading="isCancelling"
          @click="handleCancel"
        >
          Cancel all
        </UButton>
        <UTooltip :text="analyzeLink ? 'Compare the completed experiments to a ground-truth column' : 'Available once an experiment has completed'">
          <UButton
            color="primary"
            icon="i-lucide-chart-column"
            size="sm"
            :disabled="!analyzeLink"
            :to="analyzeLink"
          >
            Analyze
          </UButton>
        </UTooltip>
        <UButton
          variant="outline"
          color="error"
          icon="i-lucide-trash-2"
          size="sm"
          @click="() => { showDeleteDialog = true }"
        >
          Delete
        </UButton>
      </AppPageActions>

      <div>
        <h1 class="flex items-center gap-2.5 text-xl font-semibold text-highlighted">
          <UIStatusIcon :status="batch.status" size="size-5" tooltip />
          <span class="min-w-0 text-balance">{{ batch.name }}</span>
        </h1>
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <UIMetaItem icon="i-lucide-hash" label="Batch" class="tabular-nums">
            {{ batch.id }}
          </UIMetaItem>
          <UIMetaItem icon="i-lucide-calendar" label="Created" class="tabular-nums">
            {{ formatDate(batch.created_at) }}
          </UIMetaItem>
          <UIMetaItem v-if="batch.dataset_name" icon="i-lucide-database" label="Dataset">
            <span class="truncate text-toned">{{ batch.dataset_name }}</span>
          </UIMetaItem>
          <UIMetaItem v-if="batch.base_experiment_id" icon="i-lucide-git-fork" label="Derived from">
            <NuxtLink :to="`/experiments/${batch.base_experiment_id}`" class="truncate text-toned underline-offset-2 hover:text-highlighted hover:underline">
              {{ batch.base_experiment_name }}
            </NuxtLink>
          </UIMetaItem>
        </div>
        <p v-if="batch.description" class="mt-2 max-w-prose whitespace-pre-wrap text-sm text-toned text-pretty">
          {{ batch.description }}
        </p>
      </div>

      <dl class="flex flex-wrap gap-x-10 gap-y-4">
        <div>
          <dt class="text-xs text-muted">
            Completed
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            {{ finished }} / {{ batch.experiments.length }}
          </dd>
        </div>
        <div v-if="batch.counts.failed">
          <dt class="text-xs text-muted">
            Failed
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-error tabular-nums">
            {{ batch.counts.failed }}
          </dd>
        </div>
        <div v-for="axis in axes" :key="axis.key">
          <dt class="text-xs text-muted">
            {{ axis.title }}
          </dt>
          <dd v-if="axis.providerGroups.length" class="mt-0.5 flex flex-col gap-0.5 text-sm text-highlighted">
            <span v-for="group in axis.providerGroups" :key="group.key" class="inline-flex items-center gap-1.5">
              <UIProviderIcon v-if="group.key" :provider="group.key" />
              <span v-if="group.label" class="text-muted">{{ group.label }}</span>
              {{ group.names.join(', ') }}
            </span>
          </dd>
          <dd v-else class="mt-0.5 text-sm text-highlighted">
            {{ axis.values.join(', ') }}
          </dd>
        </div>
      </dl>

      <ExperimentsSection id="experiments" title="Experiments" description="One experiment per combination. Open one to see its configuration and executions.">
        <div class="overflow-x-auto rounded-lg border border-default">
          <table class="w-full text-sm">
            <thead class="border-b border-default text-left text-xs text-muted">
              <tr>
                <th v-for="axis in axes" :key="axis.key" scope="col" class="px-4 py-2 font-medium">
                  {{ axis.title }}
                </th>
                <th scope="col" class="px-4 py-2 font-medium">
                  Status
                </th>
                <th scope="col" class="px-4 py-2 text-right font-medium">
                  Rows
                </th>
                <th scope="col" class="px-4 py-2 text-right font-medium">
                  Tokens
                </th>
                <th scope="col" class="px-4 py-2 text-right font-medium">
                  Cost
                </th>
                <th scope="col" class="px-4 py-2 text-right font-medium">
                  Duration
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-default">
              <tr v-for="experiment in batch.experiments" :key="experiment.id" class="relative hover:bg-elevated/50">
                <td v-for="(axis, index) in axes" :key="axis.key" class="px-4 py-2.5">
                  <!-- Stretched link on the first cell: the whole row opens the experiment -->
                  <NuxtLink
                    v-if="index === 0"
                    :to="`/experiments/${experiment.id}`"
                    class="font-medium text-highlighted outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-primary"
                  >
                    <ModelsLabel v-if="axis.field === 'model_id'" :name="labelOf(experiment, axis)" :provider="providerOf(experiment, axis)" />
                    <template v-else>
                      {{ labelOf(experiment, axis) }}
                    </template>
                  </NuxtLink>
                  <ModelsLabel v-else-if="axis.field === 'model_id'" class="text-toned" :name="labelOf(experiment, axis)" :provider="providerOf(experiment, axis)" />
                  <span v-else class="text-toned">{{ labelOf(experiment, axis) }}</span>
                </td>
                <td class="px-4 py-2.5">
                  <UIStatusBadge :status="experiment.status" />
                </td>
                <td class="px-4 py-2.5 text-right">
                  <UIRowCount :rows="experiment.row_count" tone="quiet" />
                </td>
                <td class="px-4 py-2.5 text-right tabular-nums text-toned">
                  {{ experiment.total_tokens?.toLocaleString() ?? '—' }}
                </td>
                <td class="px-4 py-2.5 text-right tabular-nums text-toned">
                  {{ formatCost(experiment.total_cost_usd) }}
                </td>
                <td class="px-4 py-2.5 text-right tabular-nums text-toned">
                  {{ experiment.duration_seconds === null ? '—' : formatDuration(experiment.duration_seconds) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </ExperimentsSection>
    </div>

    <UModal v-model:open="showDeleteDialog" title="Delete batch?">
      <template #body>
        <p class="text-sm text-toned text-pretty">
          Only the grouping is removed. Its {{ batch?.experiments.length }} experiments, executions and results are kept as ordinary experiments.
        </p>
      </template>
      <template #footer>
        <div class="flex gap-3 w-full justify-end">
          <UButton variant="outline" color="neutral" @click="() => { showDeleteDialog = false }">
            Cancel
          </UButton>
          <UButton variant="solid" color="error" :loading="isDeleting" @click="handleDelete">
            Delete batch
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
