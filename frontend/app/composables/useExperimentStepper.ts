/**
 * Composable for managing stepper navigation and modal state
 */
export function useExperimentStepper(allPromptVersions: Ref<any[] | null | undefined> = ref(null)) {
  // Stepper state
  const currentStep = ref(0)
  const stepper = useTemplateRef<any>('stepper')
  const isSubmitting = ref(false)

  // Modal state for prompt details
  const showPromptDetailsModal = ref(false)
  const selectedPromptVersionForDetails = ref<any>(null)

  // Navigation helpers
  const canGoNext = computed(() => {
    return stepper.value?.hasNext
  })

  const canGoPrev = computed(() => {
    return stepper.value?.hasPrev
  })

  function nextStep() {
    if (canGoNext.value) {
      stepper.value?.next()
    }
  }

  function prevStep() {
    if (canGoPrev.value) {
      stepper.value?.prev()
    }
  }

  // Modal handlers
  function openPromptDetails(promptVersionId: number) {
    const promptVersion = allPromptVersions.value?.find(v => v.id === promptVersionId)
    if (promptVersion) {
      selectedPromptVersionForDetails.value = promptVersion
      showPromptDetailsModal.value = true
    }
  }

  function closePromptDetails() {
    showPromptDetailsModal.value = false
  }

  return {
    // State
    currentStep,
    stepper,
    isSubmitting,
    showPromptDetailsModal,
    selectedPromptVersionForDetails,

    // Computed
    canGoNext,
    canGoPrev,

    // Methods
    nextStep,
    prevStep,
    openPromptDetails,
    closePromptDetails,
  }
}
