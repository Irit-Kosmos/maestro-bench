<script setup lang="ts">
import type { Prompt } from '~/types'

// Page meta
definePageMeta({
  title: 'Prompts',
  subtitle: 'Manage your reusable prompts with versioning support',
})

// Fetch data directly in the page
const { data: prompts, pending, error, refresh } = await useMyLazyFetch<Prompt[]>('/prompts')

// Composables
const { createPrompt } = usePrompts()
const { showCreateSuccess, showCreateError } = useStandardToast()

// Page meta
useSeoMeta({
  title: 'Prompts',
  description: 'Manage your reusable prompts with versioning support',
})

// State
const showCreateModal = ref(false)
const isCreating = ref(false)

const createForm = ref({
  name: '',
  description: '',
  category: '',
})

// Computed
const createFormValid = computed(() => {
  return createForm.value.name.trim()
})

// Methods
function resetCreateForm() {
  createForm.value = {
    name: '',
    description: '',
    category: '',
  }
}

async function handleCreatePrompt() {
  if (!createFormValid.value)
    return

  isCreating.value = true
  try {
    const result = await createPrompt({
      name: createForm.value.name,
      description: createForm.value.description || undefined,
      category: createForm.value.category || undefined,
    })

    if (result.success) {
      showCreateSuccess('Prompt')
      showCreateModal.value = false
      resetCreateForm()
      // Refresh the prompts list
      await refresh()
    }
    else {
      showCreateError('Prompt', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    showCreateError('Prompt', error instanceof Error ? error.message : undefined)
  }
  finally {
    isCreating.value = false
  }
}

// Watch for modal close to reset forms
watch(() => showCreateModal.value, (newValue) => {
  if (!newValue) {
    resetCreateForm()
  }
})
</script>

<template>
  <BasePageContent
    :loading="pending"
    :error="error?.message || null"
  >
    <template #before-content>
      <Teleport to="#page-actions" defer>
        <UButton
          variant="solid"
          color="primary"
          icon="i-lucide:plus"
          size="lg"
          @click="showCreateModal = true"
        >
          Create Prompt
        </UButton>
      </Teleport>
    </template>

    <!-- Empty State -->
    <BaseEmptyState
      v-if="!prompts || prompts.length === 0"
      icon="i-lucide:message-square-text"
      title="No Prompts Found"
      description="Create your first prompt to get started with prompt versioning"
    >
      <UButton
        variant="solid"
        color="primary"
        icon="i-lucide:plus"
        size="lg"
        @click="showCreateModal = true"
      >
        Create Your First Prompt
      </UButton>
    </BaseEmptyState>

    <!-- Prompts Table -->
    <PromptsTable
      v-else
      :data="prompts"
      :loading="pending"
      @refresh="refresh"
    />

    <!-- Create Prompt Modal -->
    <UModal v-model:open="showCreateModal" :prevent-close="isCreating">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h3 class="text-lg font-semibold">
              Create New Prompt
            </h3>
          </template>

          <form class="space-y-4" @submit.prevent="handleCreatePrompt">
            <UFormField label="Prompt Name" required>
              <UInput
                v-model="createForm.name"
                placeholder="e.g., Language Evaluator"
                class="w-full"
                required
              />
            </UFormField>

            <UFormField label="Category">
              <UInput
                v-model="createForm.category"
                placeholder="e.g., evaluation, generation, analysis"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Description">
              <UTextarea
                v-model="createForm.description"
                placeholder="Describe what this prompt is used for..."
                class="w-full"
                :rows="3"
              />
            </UFormField>

            <div class="flex justify-end gap-2 pt-4 border-t border-neutral-200">
              <UButton
                type="button"
                variant="outline"
                :disabled="isCreating"
                @click="showCreateModal = false"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                :loading="isCreating"
                :disabled="!createFormValid || isCreating"
              >
                Create Prompt
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>
  </BasePageContent>
</template>
