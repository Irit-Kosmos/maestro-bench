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

import type { Experiment } from '~/types'

/**
 * Composable for managing experiments data and operations
 */
export function useExperiments() {
  const { $api } = useNuxtApp()

  // Create a new experiment
  const createExperiment = async (experimentData: { name: string, dataset_id: number }) => {
    try {
      const response = await $api('/experiments', {
        method: 'POST',
        body: experimentData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating experiment:', error)
      return { success: false, error }
    }
  }

  // Fetch a single experiment by ID
  const fetchExperiment = async (id: number) => {
    try {
      const response = await $api(`/experiments/${id}`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching experiment:', error)
      return { success: false, error }
    }
  }

  // Delete an experiment
  const deleteExperiment = async (id: number) => {
    try {
      await $api(`/experiments/${id}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting experiment:', error)
      return { success: false, error }
    }
  }

  // Re-run an experiment with the same configuration
  const rerunExperiment = async (id: number) => {
    try {
      // `queued` when the workspace is already running as many experiments as it may
      const response = await $api<{ status: 'started' | 'queued' }>(`/experiments/${id}/rerun`, {
        method: 'POST',
      })

      return { success: true as const, data: response }
    }
    catch (error) {
      console.error('Error re-running experiment:', error)
      return { success: false as const, error }
    }
  }

  // Stop a running or queued experiment; `cancelled` is false when nothing was running
  const cancelExperiment = async (id: number) => {
    try {
      const response = await $api<{ cancelled: boolean }>(`/experiments/${id}/cancel`, {
        method: 'POST',
      })

      return { success: true as const, data: response }
    }
    catch (error) {
      console.error('Error cancelling experiment:', error)
      return { success: false as const, error }
    }
  }

  // Draw a new random sample: the next run takes other rows
  const resampleExperiment = async (id: number) => {
    try {
      const response = await $api<Experiment>(`/experiments/${id}/resample`, {
        method: 'POST',
      })

      return { success: true as const, data: response }
    }
    catch (error) {
      console.error('Error resampling experiment:', error)
      return { success: false as const, error }
    }
  }

  return {
    createExperiment,
    fetchExperiment,
    deleteExperiment,
    rerunExperiment,
    cancelExperiment,
    resampleExperiment,
  }
}
