// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import { apiErrorMessage } from '~/composables/useAnalyses'

/**
 * Composable for handling experiment submission
 */
export function useExperimentSubmission() {
  const { createExperiment } = useExperiments()
  const { createBatch } = useBatches()
  const { ok, fail } = useStandardToast()
  const { assignStudies } = useStudies()
  const router = useRouter()

  // What was just created goes into the studies picked on the form. The creation stands if this fails.
  async function putInStudies(kind: 'experiment' | 'batch', id: number, studyIds: number[]) {
    if (!studyIds.length)
      return
    try {
      await assignStudies(kind, [id], { add: studyIds })
    }
    catch (error) {
      fail('Couldn’t add it to the studies', apiErrorMessage(error) ?? 'You can do it from its page.')
    }
  }

  async function handleSubmit(experimentData: any, studyIds: number[] = []) {
    try {
      const result = await createExperiment(experimentData)

      if (result.success) {
        const created = result.data as { id: number, status?: string }
        await putInStudies('experiment', created.id, studyIds)
        // A workspace already running as many experiments as it may queues the new one
        ok(created.status === 'queued' ? 'Experiment queued' : 'Experiment started')
        // Land on the run itself: its progress is live there
        await navigateTo(`/experiments/${created.id}`)
        return { success: true }
      }
      else {
        // An aggregator the backend cannot run says why
        fail('Couldn’t create the experiment', apiErrorMessage(result.error) ?? 'Please try again.')
        return { success: false, error: 'Creation failed' }
      }
    }
    catch (error) {
      console.error('Error creating experiment:', error)
      fail('Couldn’t create the experiment', 'An unexpected error occurred. Please try again.')
      return { success: false, error }
    }
  }

  // One experiment per combination of the variations, started together
  async function handleBatchSubmit(batch: Parameters<typeof createBatch>[0], experimentCount: number, studyIds: number[] = []) {
    const result = await createBatch(batch)
    if (result.success) {
      await putInStudies('batch', result.data.id, studyIds)
      ok('Batch started', { description: `${experimentCount} experiments are running.` })
      await navigateTo(`/batches/${result.data.id}`)
      return { success: true }
    }
    fail('Couldn’t create the batch', apiErrorMessage(result.error) ?? 'Please try again.')
    return { success: false, error: result.error }
  }

  // Back to where the person came from; a page opened directly has nowhere to go back to
  async function handleCancel() {
    if (router.options.history.state.back)
      router.back()
    else
      await navigateTo('/experiments')
  }

  return {
    handleSubmit,
    handleBatchSubmit,
    handleCancel,
  }
}
