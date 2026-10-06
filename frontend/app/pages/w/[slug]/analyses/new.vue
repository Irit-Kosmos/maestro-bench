<script setup lang="ts">
import type { AnalysisForm, AnalysisResult } from '~/types'
import { apiErrorMessage, DEFAULT_ANALYSIS_CONFIG } from '~/composables/useAnalyses'

definePageMeta({
  title: 'New Analysis',
  requiresRole: 'editor',
})

useSeoMeta({ title: 'New Analysis' })

const route = useRoute()
const { createAnalysis, computeAnalysis } = useAnalyses()
const { showCreateSuccess, showCreateError, fail } = useStandardToast()

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
  tag_ids: [],
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

const canSave = computed(() => canCompute.value && !!form.value.name.trim())

async function runPreview() {
  isComputing.value = true
  try {
    preview.value = await computeAnalysis(form.value.config, form.value.runs)
  }
  catch (error) {
    fail('Couldn’t compute the analysis', apiErrorMessage(error))
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

// ⌘↵ creates the analysis, from any field
defineShortcuts({
  meta_enter: {
    usingInput: true,
    handler: () => {
      if (canSave.value && !isSaving.value)
        save()
    },
  },
})
</script>

<template>
  <BasePageContent>
    <AppPageActions>
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-arrows-clockwise-bold"
        size="sm"
        :loading="isComputing"
        :disabled="!canCompute"
        @click="runPreview"
      >
        Preview
      </UButton>
      <UButton
        variant="soft"
        color="neutral"
        icon="i-ph-check-bold"
        size="sm"
        :loading="isSaving"
        :disabled="!canSave"
        @click="save"
      >
        Create analysis
        <template #trailing>
          <span class="flex gap-0.5">
            <BaseKbd value="meta" />
            <BaseKbd value="enter" />
          </span>
        </template>
      </UButton>
    </AppPageActions>

    <div class="mx-auto max-w-3xl space-y-10 pb-10">
      <AnalysesEditor v-model="form" />

      <section v-if="preview" class="border-t border-default pt-8">
        <AnalysesResults :result="preview" :config="form.config" :name="form.name" />
      </section>
    </div>
  </BasePageContent>
</template>
