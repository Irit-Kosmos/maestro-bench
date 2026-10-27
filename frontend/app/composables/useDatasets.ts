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

import type { CreateDatasetForm, Dataset, DatasetAgreement, DatasetStats } from '~/types'

/**
 * Composable for managing datasets data and operations
 */
export function useDatasets() {
  const { $api } = useNuxtApp()

  // Create a dataset from a file: the file is the request body, the rest goes in the query
  async function createDataset({ name, description, file }: CreateDatasetForm) {
    try {
      const response = await $api<Dataset>('/datasets/upload', {
        method: 'POST',
        query: { filename: file.name, name, description },
        headers: { 'Content-Type': file.type || 'application/octet-stream' },
        body: file,
      })

      return { success: true as const, data: response }
    }
    catch (error) {
      console.error('Error creating dataset:', error)
      // The API says what is wrong with the file (too large, not a CSV...)
      const detail = (error as { data?: { detail?: unknown } }).data?.detail
      return { success: false as const, error: typeof detail === 'string' ? detail : undefined }
    }
  }

  // Rename or describe a dataset; the file is edited through its rows. An empty description clears it
  function updateDataset(id: number, patch: { name?: string, description?: string | null }) {
    return $api<Dataset>(`/datasets/${id}`, { method: 'PUT', body: patch })
  }

  // Delete a dataset
  async function deleteDataset(id: number) {
    try {
      await $api(`/datasets/${id}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting dataset:', error)
      return { success: false, error }
    }
  }

  // Check if a dataset can be previewed
  function canPreview(dataset: Dataset): boolean {
    if (!dataset.file_path)
      return false

    const extension = dataset.file_path.toLowerCase().split('.').pop()
    return extension === 'csv' || extension === 'json'
  }

  // Get file extension from dataset
  function getFileExtension(dataset: Dataset): string | null {
    if (!dataset.file_path)
      return null

    return dataset.file_path.toLowerCase().split('.').pop() || null
  }

  // Get dataset statistics including experiment count
  async function getDatasetStats(id: number) {
    try {
      const response = await $api<DatasetStats>(`/datasets/${id}/stats`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching dataset stats:', error)
      return { success: false, error }
    }
  }

  // Agreement between columns that rate the same rows, computed from the saved file
  const fetchAgreement = (id: number, columns: string[]) =>
    $api<DatasetAgreement>(`/datasets/${id}/agreement`, { query: { columns } })

  // Get a single dataset by ID
  async function getDataset(id: number) {
    try {
      const response = await $api<Dataset>(`/datasets/${id}`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching dataset:', error)
      return { success: false, error }
    }
  }

  return {
    createDataset,
    updateDataset,
    deleteDataset,
    getDataset,
    getDatasetStats,
    fetchAgreement,
    canPreview,
    getFileExtension,
  }
}
