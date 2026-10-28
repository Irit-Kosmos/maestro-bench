<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Analysis, AnalysisForm, AnalysisResult } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const route = useRoute()
const analysisId = computed(() => Number.parseInt(route.params.id as string))

const { fetchResults, updateAnalysis, deleteAnalysis } = useAnalyses()
const { canEdit } = useCurrentWorkspace()
const { isShared } = useShare()
const { formatDate } = useUIHelpers()
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

// The print stylesheet (see the default layout) turns the page into the report; the browser's dialog writes the PDF
const { print: exportPdf } = usePrinting()

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
  <BasePageContent
    :loading="pending && !analysis"
    :error="!analysis && !!error"
    :error-kind="fetchErrorKind(error)"
    back-to="/analyses"
    back-label="Back to analyses"
    @retry="refreshAnalysis()"
  >
    <div v-if="analysis" class="space-y-4 pb-6">
      <AppPageActions>
        <UButton
          variant="ghost"
          color="neutral"
          icon="i-ph-arrows-clockwise-bold"
          size="sm"
          :loading="isComputing"
          @click="compute"
        >
          Recompute
        </UButton>
        <UButton
          data-tooltip="Opens the print dialog: choose “Save as PDF”"
          variant="ghost"
          color="neutral"
          icon="i-ph-file-pdf-bold"
          size="sm"
          :disabled="!result || isComputing"
          @click="exportPdf"
        >
          Export PDF
        </UButton>
        <UIGuardedButton variant="soft" color="neutral" icon="i-ph-pencil-simple-bold" size="sm" @click="openEditor">
          Edit
        </UIGuardedButton>
        <SharesButton v-if="analysis" kind="analysis" :item-id="analysis.id" />
        <UDropdownMenu
          v-if="canEdit"
          :items="[{ label: 'Delete analysis', icon: 'i-ph-trash-bold', color: 'error', onSelect: () => { showDeleteDialog = true } }]"
          :content="{ align: 'end' }"
        >
          <UButton icon="i-ph-dots-three-bold" color="neutral" variant="ghost" size="sm" aria-label="More actions" />
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
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <UIMetaItem icon="i-ph-hash-bold" label="Analysis">
            {{ analysis.id }}
          </UIMetaItem>
          <UIMetaItem icon="i-ph-calendar-blank-bold" label="Created">
            {{ formatDate(analysis.created_at) }}
          </UIMetaItem>
          <UIPerson v-if="analysis.author" :person="analysis.author" label="Created by" />
        </div>
        <p v-if="analysis.description" class="mt-1 text-sm text-toned max-w-prose">
          {{ analysis.description }}
        </p>
        <div v-if="analysis.tags.length" class="mt-2 flex flex-wrap gap-1">
          <TagsChip v-for="tag in analysis.tags" :key="tag.id" :tag="tag" />
        </div>
        <StudiesItemStudies v-if="!isShared" :id="analysis.id" kind="analysis" class="mt-2.5" />
      </div>

      <BaseErrorState v-if="computeError" :message="computeError" />
      <BaseLoadingState v-else-if="isComputing && !result" />
      <BaseEmptyState
        v-else-if="result && result.runs.length === 0"
        title="No executions"
        message="Edit the analysis to add executions to compare."
        icon="i-ph-chart-bar-bold"
      />
      <AnalysesResults v-else-if="result" :result="result" :config="analysis.config" :name="analysis.name" />

      <ExperimentsSection v-if="!isShared" id="notes" class="print:hidden" title="Notes" icon="i-ph-notepad-bold" description="What you notice and decide about this comparison. Notes show up in the activity of every study that holds it.">
        <NotesJournal kind="analysis" :item-id="analysis.id" />
      </ExperimentsSection>
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
          <UButton color="primary" icon="i-ph-floppy-disk-bold" :loading="isSaving" @click="saveDraft">
            Save and recompute
          </UButton>
        </div>
      </template>
    </USlideover>

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete analysis?"
      message="Executions and their results are kept. Only this comparison is removed."
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="confirmDelete"
    />
  </BasePageContent>
</template>
