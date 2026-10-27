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

import type { Variation } from '~/types'

/**
 * Composable for batches: groups of experiments generated from one base
 * configuration by varying a model, a prompt version or a temperature.
 */
export function useBatches() {
  const { $api } = useNuxtApp()

  async function createBatch(batch: {
    name: string
    description?: string
    base_experiment_id?: number
    config: Record<string, unknown>
    variations: Variation[]
    skip_base_point?: boolean
  }) {
    try {
      return { success: true as const, data: await $api<{ id: number }>('/batches', { method: 'POST', body: batch }) }
    }
    catch (error) {
      console.error('Error creating batch:', error)
      return { success: false as const, error }
    }
  }

  async function cancelBatch(id: number) {
    try {
      return { success: true as const, data: await $api<{ cancelled: number }>(`/batches/${id}/cancel`, { method: 'POST' }) }
    }
    catch (error) {
      console.error('Error cancelling batch:', error)
      return { success: false as const, error }
    }
  }

  async function rerunBatch(id: number) {
    try {
      return { success: true as const, data: await $api<{ started: number, skipped: number }>(`/batches/${id}/rerun`, { method: 'POST' }) }
    }
    catch (error) {
      console.error('Error re-running batch:', error)
      return { success: false as const, error }
    }
  }

  async function deleteBatch(id: number) {
    try {
      await $api(`/batches/${id}`, { method: 'DELETE' })
      return { success: true as const }
    }
    catch (error) {
      console.error('Error deleting batch:', error)
      return { success: false as const, error }
    }
  }

  return { createBatch, cancelBatch, rerunBatch, deleteBatch }
}
