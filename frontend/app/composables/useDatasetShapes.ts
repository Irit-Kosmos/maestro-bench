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

export interface DatasetShape {
  headers: string[]
  total_rows: number
}

/**
 * Columns and number of rows of several datasets, each one read once from its preview.
 * A dataset not read yet, or that could not be, has no shape.
 */
export function useDatasetShapes() {
  const { $api } = useNuxtApp()
  const shapes = reactive<Record<number, DatasetShape>>({})
  const failed = reactive(new Set<number>())
  const pending = new Set<number>()

  async function load(id: number) {
    if (shapes[id] || pending.has(id))
      return
    pending.add(id)
    failed.delete(id)
    try {
      const preview = await $api<DatasetShape>(`/datasets/${id}/preview`)
      shapes[id] = { headers: preview.headers, total_rows: preview.total_rows }
    }
    catch (error) {
      console.error('Error loading dataset preview:', error)
      failed.add(id)
    }
    finally {
      pending.delete(id)
    }
  }

  return {
    shapeOf: (id: number): DatasetShape | undefined => shapes[id],
    hasFailed: (id: number) => failed.has(id),
    load,
  }
}
