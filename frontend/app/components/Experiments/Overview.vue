<script setup lang="ts">
import type { Experiment, ExperimentExecution } from '~/types'

interface Props {
  experiment: Experiment
  executions: ExperimentExecution[]
  latestExecution?: ExperimentExecution | null
}

const props = defineProps<Props>()

const { formatDuration } = useUIHelpers()

// Computed
const duration = computed(() => {
  return props.experiment
    ? formatDuration(
        props.experiment.completed_at
          ? new Date(props.experiment.completed_at).getTime() / 1000
          - new Date(props.experiment.created_at).getTime() / 1000
          : 0,
      )
    : 'N/A'
})
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <UIcon name="i-lucide:flask-conical" class="h-6 w-6" />
          <h2 class="text-xl font-semibold text-neutral-900">
            Experiment Overview
          </h2>
        </div>
        <UIStatusBadge
          :status="experiment.status || 'pending'"
          variant="subtle"
        />
      </div>
    </template>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Created
        </dt>
        <dd class="text-lg font-semibold text-neutral-900">
          {{ new Date(experiment.created_at).toLocaleDateString() }}
        </dd>
      </div>
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Dataset
        </dt>
        <dd class="text-lg font-semibold text-neutral-900">
          {{ experiment.dataset?.name || 'Unknown' }}
        </dd>
      </div>
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Executions
        </dt>
        <dd class="text-lg font-semibold text-neutral-900">
          {{ executions.length }}
        </dd>
      </div>
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Agents
        </dt>
        <dd class="text-lg font-semibold text-neutral-900">
          {{ latestExecution?.agent_executions?.length || 0 }}
        </dd>
      </div>
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Duration
        </dt>
        <dd class="text-lg font-semibold text-neutral-900">
          {{ experiment.status === 'completed' ? duration : '-' }}
        </dd>
      </div>
    </div>

    <!-- Results File Info -->
    <div v-if="latestExecution?.results_file_path" class="mt-6 pt-6 border-t border-neutral-200">
      <div class="flex items-center justify-between">
        <div>
          <dt class="text-sm font-medium text-neutral-500 mb-1">
            Results File
          </dt>
          <dd class="text-sm text-neutral-900 font-mono">
            {{ latestExecution.results_file_path }}
          </dd>
        </div>
        <UButton
          variant="outline"
          color="neutral"
          icon="i-lucide-download"
          size="sm"
          :disabled="!latestExecution.results_file_path"
        >
          Download Results
        </UButton>
      </div>
    </div>
  </UCard>
</template>
