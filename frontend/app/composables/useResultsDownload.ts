export function useResultsDownload() {
  const { fail } = useStandardToast()
  const runtimeConfig = useRuntimeConfig()
  const { slug } = useWorkspace()

  /**
   * Download results for a specific execution
   */
  async function downloadResults(executionId: number) {
    try {
      // Create a direct fetch to the download endpoint
      const response = await fetch(`${runtimeConfig.public.BACK_URL}/workspaces/${slug.value}/executions/${executionId}/results`, {
        credentials: 'include',
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
