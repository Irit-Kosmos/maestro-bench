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

export function useResultsDownload() {
  const { fail } = useStandardToast()
  const runtimeConfig = useRuntimeConfig()
  const route = useRoute()

  /**
   * Download results for a specific execution
   */
  async function downloadResults(executionId: number) {
    try {
      // Create a direct fetch to the download endpoint
      const response = await fetch(`${runtimeConfig.public.BACK_URL}${scopeApiPath(`/executions/${executionId}/results`, route.path)}`, {
        // A public link is read without an account
        credentials: shareOfPath(route.path) ? 'omit' : 'include',
        headers: {
          Accept: 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to download results' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      // Get the filename from the Content-Disposition header or generate one
      const filename = `execution_${executionId}_results.json`

      // Create blob and download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()

      // Cleanup
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      return { success: true }
    }
    catch (error: any) {
      console.error('Error downloading results:', error)

      fail('Couldn’t download the results', error.message || 'Failed to download results file')

      return { success: false, error: error.message }
    }
  }

  return {
    downloadResults,
  }
}
