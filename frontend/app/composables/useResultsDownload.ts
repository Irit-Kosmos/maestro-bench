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

/** The file name a download gives in its Content-Disposition, or `fallback` */
function filenameOf(response: Response, fallback: string): string {
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1]
  if (encoded) {
    try {
      return decodeURIComponent(encoded)
    }
    catch {}
  }
  return /filename="([^"]+)"/i.exec(disposition)?.[1] ?? fallback
}

function save(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export function useResultsDownload() {
  const { fail, info } = useStandardToast()
  const runtimeConfig = useRuntimeConfig()
  const route = useRoute()

  /** Fetch a file of the API (of the workspace, or of the link the page is under) and save it */
  async function fetchFile(request: string, fallbackName: string): Promise<Response> {
    const response = await fetch(`${runtimeConfig.public.BACK_URL}${scopeApiPath(request, route.path)}`, {
      // A public link is read without an account
      credentials: shareOfPath(route.path) ? 'omit' : 'include',
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(typeof errorData.detail === 'string' ? errorData.detail : `HTTP ${response.status}`)
    }
    save(await response.blob(), filenameOf(response, fallbackName))
    return response
  }

  /**
   * Download results for a specific execution
   */
  async function downloadResults(executionId: number) {
    try {
      await fetchFile(`/executions/${executionId}/results`, `execution_${executionId}_results.json`)
      return { success: true }
    }
    catch (error: any) {
      fail('Couldn’t download the results', error.message || 'Failed to download results file')
      return { success: false, error: error.message }
    }
  }

  const downloadingZip = ref(false)

  /** The results of experiments, in a .zip file, and a word on those that had none */
  async function downloadZip(request: string): Promise<void> {
    downloadingZip.value = true
    try {
      const response = await fetchFile(request, 'maestro-results.zip')
      const skipped = Number(response.headers.get('X-Skipped-Experiments') ?? 0)
      if (skipped > 0) {
        info(
          `${skipped} ${skipped > 1 ? 'experiments were' : 'experiment was'} left out`,
          'Only experiments with a completed execution have results to download.',
        )
      }
    }
    catch (error: any) {
      fail('Couldn’t download the results', error.message)
    }
    finally {
      downloadingZip.value = false
    }
  }

  /** Every experiment of a batch */
  function downloadBatch(batchId: number) {
    return downloadZip(`/batches/${batchId}/results`)
  }

  /** Batches (all their experiments) and experiments, in one file */
  function downloadSelection({ batchIds = [], experimentIds = [] }: { batchIds?: number[], experimentIds?: number[] }) {
    const query = new URLSearchParams([
      ...batchIds.map(id => ['batch_id', String(id)]),
      ...experimentIds.map(id => ['experiment_id', String(id)]),
    ])
    return downloadZip(`/results/download?${query}`)
  }

  return {
    downloadResults,
    downloadBatch,
    downloadSelection,
    downloadingZip,
  }
}
