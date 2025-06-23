export function useResultsDownload() {
  const { $api } = useNuxtApp()
  const toast = useToast()
  const runtimeConfig = useRuntimeConfig()

  /**
   * Download results for a specific execution
   */
  async function downloadResults(executionId: number, experimentName?: string) {
    try {
      // Create a direct fetch to the download endpoint
      const response = await fetch(`${runtimeConfig.public.BACK_URL}/executions/${executionId}/download-results`, {
        headers: {
          'Accept': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to download results' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      // Get the filename from the Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `execution_${executionId}_results.json`

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

      toast.add({
        title: 'Success',
        description: 'Results downloaded successfully',
        color: 'success',
        icon: 'i-lucide:download',
      })

      return { success: true }
    }
    catch (error: any) {
      console.error('Error downloading results:', error)
      
      toast.add({
        title: 'Download Failed',
        description: error.message || 'Failed to download results file',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })

      return { success: false, error: error.message }
    }
  }

  return {
    downloadResults,
  }
}
