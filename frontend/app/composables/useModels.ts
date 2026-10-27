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

/**
 * Composable for managing LLM models
 */
export function useModels() {
  const { $api } = useNuxtApp()

  // Create a new model
  async function createModel(modelData: {
    name: string
    provider: string
    description?: string
    max_tokens?: number
    is_active?: boolean
  }) {
    try {
      const response = await $api('/models', {
        method: 'POST',
        body: modelData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating model:', error)
      return { success: false, error: 'Failed to create model' }
    }
  }

  // Update a model
  async function updateModel(modelId: number, modelData: {
    name?: string
    provider?: string
    description?: string
    max_tokens?: number
    is_active?: boolean
  }) {
    try {
      const response = await $api(`/models/${modelId}`, {
        method: 'PUT',
        body: modelData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating model:', error)
      return { success: false, error: 'Failed to update model' }
    }
  }

  // Delete a model
  async function deleteModel(modelId: number) {
    try {
      await $api(`/models/${modelId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting model:', error)
      return { success: false, error: 'Failed to delete model' }
    }
  }

  // Toggle model active status
  async function toggleModelStatus(modelId: number) {
    try {
      const response = await $api(`/models/${modelId}/toggle-status`, {
        method: 'PATCH',
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error toggling model status:', error)
      return { success: false, error: 'Failed to toggle model status' }
    }
  }

  return {
    createModel,
    updateModel,
    deleteModel,
    toggleModelStatus,
  }
}
