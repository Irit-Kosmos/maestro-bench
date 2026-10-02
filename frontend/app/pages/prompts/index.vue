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
  tag_ids: [] as number[],
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
    tag_ids: [],
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
      tag_ids: createForm.value.tag_ids,
    })

    if (result.success) {
      showCreateSuccess('Prompt')
      showCreateModal.value = false
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
</script>

<template>
  <BasePageContent
    :loading="pending"
    :error="error?.message || null"
  >
    <template #before-content>
      <UButton
        color="neutral"
        variant="soft"
        icon="i-lucide-plus"
        size="sm"
        @click="() => { showCreateModal = true }"
      >
        New prompt
      </UButton>
    </template>

    <!-- Empty State -->
    <BaseEmptyState
      v-if="!prompts || prompts.length === 0"
      icon="i-lucide-message-square-text"
      title="No prompts yet"
      message="Prompts are versioned, so you can change one and compare results across versions."
      action-label="New prompt"
      @action="() => { showCreateModal = true }"
    />

    <!-- Prompts Table -->
    <PromptsTable
      v-else
      :data="prompts"
      :loading="pending"
      @refresh="refresh"
    />

    <!-- Create Prompt Modal -->
    <UModal v-model:open="showCreateModal" :prevent-close="isCreating" @after:leave="resetCreateForm">
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

            <UFormField label="Tags">
              <TagsInput v-model="createForm.tag_ids" />
            </UFormField>

            <div class="flex justify-end gap-2 pt-4 border-t border-default">
              <UButton
                type="button"
                variant="outline"
                :disabled="isCreating"
                @click="() => { showCreateModal = false }"
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
