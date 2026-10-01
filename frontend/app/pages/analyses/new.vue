<script setup lang="ts">
import type { AnalysisForm, AnalysisResult } from '~/types'
import { apiErrorMessage, DEFAULT_ANALYSIS_CONFIG } from '~/composables/useAnalyses'

definePageMeta({
  title: 'New Analysis',
})

useSeoMeta({ title: 'New Analysis' })

const route = useRoute()
const { createAnalysis, computeAnalysis } = useAnalyses()
const { showCreateSuccess, showCreateError } = useStandardToast()
const toast = useToast()

// ?execution=<id>&name=<experiment name> pre-fills from an experiment page,
// ?executions=<id>,<id>&name=<batch name> from a batch
const executionId = Number(route.query.execution)
const executionIds = String(route.query.executions ?? '')
  .split(',')
  .map(Number)
  .filter(id => Number.isInteger(id) && id > 0)
const form = ref<AnalysisForm>({
  name: route.query.name ? `${route.query.name} analysis` : '',
  description: null,
  config: structuredClone(DEFAULT_ANALYSIS_CONFIG),
  runs: executionIds.length > 0
    ? executionIds.map(id => ({ execution_id: id, agent_name: '', label: null }))
    : Number.isFinite(executionId) && executionId > 0
      ? [{ execution_id: executionId, agent_name: '', label: null }]
      : [],
})

const preview = ref<AnalysisResult | null>(null)
const isComputing = ref(false)
const isSaving = ref(false)

const canCompute = computed(() =>
  form.value.runs.length > 0
  && form.value.runs.every(r => r.agent_name)
  && !!form.value.config.truth_column
  && form.value.config.metrics.length > 0,
)

async function runPreview() {
  isComputing.value = true
  try {
    preview.value = await computeAnalysis(form.value.config, form.value.runs)
  }
  catch (error) {
    toast.add({ title: 'Error', description: apiErrorMessage(error) ?? 'Failed to compute analysis', color: 'error' })
  }
  finally {
    isComputing.value = false
  }
}

async function save() {
  isSaving.value = true
  try {
    const analysis = await createAnalysis(form.value)
    showCreateSuccess('Analysis')
    await navigateTo(`/analyses/${analysis.id}`)
  }
  catch (error) {
    showCreateError('Analysis', apiErrorMessage(error))
  }
  finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="space-y-4 pb-6">
    <UCard>
      <AnalysesEditor v-model="form" />
      <template #footer>
        <div class="flex justify-end gap-3">
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-refresh-cw"
            :loading="isComputing"
            :disabled="!canCompute"
            @click="runPreview"
          >
            Preview
          </UButton>
          <UButton
            color="primary"
            icon="i-lucide-save"
            :loading="isSaving"
            :disabled="!canCompute || !form.name"
            @click="save"
          >
            Save analysis
          </UButton>
        </div>
      </template>
    </UCard>

    <AnalysesResults v-if="preview" :result="preview" :config="form.config" :name="form.name" />
  </div>
</template>
