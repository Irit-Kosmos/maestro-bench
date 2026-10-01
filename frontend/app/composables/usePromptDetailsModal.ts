import type { PromptVersion } from '~/types'

/**
 * State of the "prompt details" modal, opened from an agent's prompt version.
 */
export function usePromptDetailsModal(allPromptVersions: Ref<PromptVersion[] | null | undefined>) {
  const showPromptDetailsModal = ref(false)
  const selectedPromptVersionForDetails = ref<PromptVersion | null>(null)

  function openPromptDetails(promptVersionId: number) {
    const promptVersion = allPromptVersions.value?.find(v => v.id === promptVersionId)
    if (promptVersion) {
      selectedPromptVersionForDetails.value = promptVersion
      showPromptDetailsModal.value = true
    }
  }

  return {
    showPromptDetailsModal,
    selectedPromptVersionForDetails,
    openPromptDetails,
  }
}
