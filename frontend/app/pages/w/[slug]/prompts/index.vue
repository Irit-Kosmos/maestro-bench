<script setup lang="ts">
import type { Prompt } from '~/types'

// Page meta
definePageMeta({
  title: 'Prompts',
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
    tag_ids: [],
  }
}

useCreateFromQuery(() => {
  showCreateModal.value = true
})

async function handleCreatePrompt() {
  if (!createFormValid.value)
    return

  isCreating.value = true
  try {
    const result = await createPrompt({
      name: createForm.value.name,
      description: createForm.value.description || undefined,
      tag_ids: createForm.value.tag_ids,
    })

    if (result.success) {
      showCreateSuccess('Prompt')
      showCreateModal.value = false
      // A prompt does nothing without a version: go straight to writing the first one
      await navigateTo(`/prompts/${(result.data as { id: number }).id}?new=1`)
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
    :loading="pending && !prompts"
    :error="!prompts && !!error"
    :error-kind="fetchErrorKind(error)"
    @retry="refresh()"
  >
    <template #before-content>
      <UIGuardedButton
        color="neutral"
        variant="soft"
        icon="i-ph-plus-bold"
        size="sm"
        @click="() => { showCreateModal = true }"
      >
        New prompt
      </UIGuardedButton>
    </template>

    <!-- Empty State -->
    <BaseEmptyState
      v-if="!prompts || prompts.length === 0"
      icon="i-ph-chat-text-bold"
      title="No prompts yet"
      message="Prompts are versioned, so you can change one and compare results across versions."
      action-label="New prompt"
      action-requires="editor"
      @action="() => { showCreateModal = true }"
    />

    <!-- Prompts Table -->
    <PromptsTable
      v-else
      :data="prompts"
      :loading="pending"
      @refresh="refresh"
    />

    <!-- Create prompt Modal -->
    <UModal v-model:open="showCreateModal" :prevent-close="isCreating" @after:leave="resetCreateForm">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h3 class="text-lg font-semibold">
              New prompt
            </h3>
          </template>

          <form class="space-y-4" @submit.prevent="handleCreatePrompt">
            <UFormField label="Name" required>
              <UInput
                v-model="createForm.name"
                placeholder="e.g., Language Evaluator"
                class="w-full"
                required
              />
            </UFormField>

            <UFormField label="Description">
              <UTextarea
                v-model="createForm.description"
                placeholder="What this prompt is for"
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
                Create prompt
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>
  </BasePageContent>
</template>
