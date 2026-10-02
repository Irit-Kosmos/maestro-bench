<script setup lang="ts">
import type { Analysis, AnalysisForm, AnalysisResult } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const route = useRoute()
const analysisId = computed(() => Number.parseInt(route.params.id as string))

const { fetchResults, updateAnalysis, deleteAnalysis } = useAnalyses()
const { showUpdateSuccess, showUpdateError, showDeleteSuccess, showDeleteError } = useStandardToast()

const { data: analysis, pending, error, refresh: refreshAnalysis } = await useMyLazyFetch<Analysis>(
  () => `/analyses/${analysisId.value}`,
)

useSeoMeta({ title: computed(() => analysis.value?.name ?? 'Analysis') })
useBreadcrumbLabel(() => analysis.value?.name)

const result = ref<AnalysisResult | null>(null)
const isComputing = ref(false)
const computeError = ref<string | null>(null)

async function compute() {
  isComputing.value = true
  computeError.value = null
  try {
    result.value = await fetchResults(analysisId.value)
  }
  catch (e) {
    computeError.value = apiErrorMessage(e) ?? 'Failed to compute analysis'
  }
  finally {
    isComputing.value = false
  }
}

watch(analysisId, compute, { immediate: true })

// Editing happens on a copy, saved as a whole
const showEditor = ref(false)
const draft = ref<AnalysisForm | null>(null)
const isSaving = ref(false)

function openEditor() {
  if (!analysis.value)
    return
  const { name, description, config, runs, tags } = analysis.value
  draft.value = structuredClone({ name, description, config, runs, tag_ids: tags.map(tag => tag.id) })
  showEditor.value = true
}

async function saveDraft() {
  if (!draft.value)
    return
  isSaving.value = true
  try {
    await updateAnalysis(analysisId.value, draft.value)
    showUpdateSuccess('Analysis')
    showEditor.value = false
    await refreshAnalysis()
    await compute()
  }
  catch (e) {
    showUpdateError('Analysis', apiErrorMessage(e))
  }
  finally {
    isSaving.value = false
  }
}

const showDeleteDialog = ref(false)
const isDeleting = ref(false)

async function confirmDelete() {
  isDeleting.value = true
  try {
    await deleteAnalysis(analysisId.value)
    showDeleteSuccess('Analysis')
    await navigateTo('/analyses')
  }
  catch {
    showDeleteError('Analysis')
  }
  finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <BasePageContent :loading="pending" :error="error ? 'Analysis not found' : null">
    <div v-if="analysis" class="space-y-4 pb-6">
      <AppPageActions>
        <UButton
          variant="ghost"
          color="neutral"
          icon="i-lucide-refresh-cw"
          size="sm"
          :loading="isComputing"
          @click="compute"
        >
          Recompute
        </UButton>
        <UButton variant="soft" color="neutral" icon="i-lucide-pencil" size="sm" @click="openEditor">
          Edit
        </UButton>
        <UDropdownMenu
          :items="[{ label: 'Delete analysis', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => { showDeleteDialog = true } }]"
          :content="{ align: 'end' }"
        >
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" aria-label="More actions" />
        </UDropdownMenu>
      </AppPageActions>

      <div>
        <h1 class="text-xl font-semibold text-highlighted text-balance">
          {{ analysis.name }}
        </h1>
        <p class="mt-0.5 text-sm text-muted">
          <span class="font-mono text-xs">{{ analysis.config.truth_column }}</span>
          vs
          <span class="font-mono text-xs">{{ analysis.config.output_path || '(whole output)' }}</span>
          · {{ analysis.config.value_type }}
          · {{ analysis.runs.length }} execution{{ analysis.runs.length === 1 ? '' : 's' }}
        </p>
        <p v-if="analysis.description" class="mt-1 text-sm text-toned max-w-prose">
          {{ analysis.description }}
        </p>
        <div v-if="analysis.tags.length" class="mt-2 flex flex-wrap gap-1">
          <TagsChip v-for="tag in analysis.tags" :key="tag.id" :tag="tag" />
        </div>
      </div>

      <BaseErrorState v-if="computeError" :message="computeError" />
      <BaseLoadingState v-else-if="isComputing && !result" />
      <BaseEmptyState
        v-else-if="result && result.runs.length === 0"
        title="No executions"
        message="Edit the analysis to add executions to compare."
        icon="i-lucide:chart-column"
      />
      <AnalysesResults v-else-if="result" :result="result" :config="analysis.config" :name="analysis.name" />
    </div>

    <USlideover v-model:open="showEditor" title="Edit analysis" :ui="{ content: 'sm:max-w-3xl' }">
      <template #body>
        <AnalysesEditor v-if="draft" v-model="draft" />
      </template>
      <template #footer>
        <div class="flex justify-end gap-3 w-full">
          <UButton variant="outline" color="neutral" @click="() => { showEditor = false }">
            Cancel
          </UButton>
          <UButton color="primary" icon="i-lucide-save" :loading="isSaving" @click="saveDraft">
            Save and recompute
          </UButton>
        </div>
      </template>
    </USlideover>

    <UModal v-model:open="showDeleteDialog" title="Delete Analysis">
      <template #body>
        <p class="text-toned">
          Delete this analysis? Executions and their results are not affected.
        </p>
      </template>
      <template #footer>
        <div class="flex gap-3 w-full justify-end">
          <UButton variant="outline" color="neutral" @click="() => { showDeleteDialog = false }">
            Cancel
          </UButton>
          <UButton variant="solid" color="error" :loading="isDeleting" @click="confirmDelete">
            Delete
          </UButton>
        </div>
      </template>
    </UModal>
  </BasePageContent>
</template>
