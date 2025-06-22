<script setup lang="ts">
import type { Prompt } from '~/types'

// Composables
const { prompts, refresh, pending, error, createPrompt } = usePrompts()
const toast = useToast()

// Page meta
useSeoMeta({
  title: 'Prompts',
  description: 'Manage your reusable prompts with versioning support',
})

// State
const showCreateModal = ref(false)
const creating = ref(false)

const newPrompt = ref({
  name: '',
  description: '',
  category: '',
})

// Methods
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}

function viewPrompt(prompt: Prompt) {
  navigateTo(`/prompts/${prompt.id}`)
}

async function handleCreatePrompt() {
  creating.value = true
  try {
    const result = await createPrompt({
      name: newPrompt.value.name,
      description: newPrompt.value.description || undefined,
      category: newPrompt.value.category || undefined,
    })

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Prompt created successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      showCreateModal.value = false
      newPrompt.value = { name: '', description: '', category: '' }
    }
    else {
      toast.add({
        title: 'Error',
        description: result.error || 'Failed to create prompt',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch {
    toast.add({
      title: 'Error',
      description: 'Error creating prompt. Please try again.',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Page Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-2xl font-bold text-neutral-900">
            Prompts
          </h1>
          <p class="text-neutral-500 mt-1">
            Manage your reusable prompts with versioning support
          </p>
        </div>
        <UButton
          variant="solid"
          color="primary"
          icon="i-lucide:plus"
          size="lg"
          @click="showCreateModal = true"
        >
          Create Prompt
        </UButton>
      </div>

      <!-- Loading State -->
      <div v-if="pending" class="flex justify-center py-12">
        <USkeleton class="h-8 w-8 rounded-full" />
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-12">
        <UIcon name="i-lucide-alert-circle" class="h-16 w-16 text-red-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          Error Loading Prompts
        </h3>
        <p class="text-neutral-600 mb-4">
          {{ error }}
        </p>
        <UButton @click="() => refresh()">
          Try Again
        </UButton>
      </div>

      <!-- Empty State -->
      <div v-else-if="!prompts || prompts.length === 0" class="text-center py-12">
        <UIcon name="i-lucide-message-square-text" class="h-16 w-16 text-neutral-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          No Prompts Found
        </h3>
        <p class="text-neutral-600 mb-6">
          Create your first prompt to get started with prompt versioning
        </p>
        <UButton
          variant="solid"
          color="primary"
          icon="i-lucide:plus"
          size="lg"
          @click="showCreateModal = true"
        >
          Create Your First Prompt
        </UButton>
      </div>

      <!-- Prompts Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <UCard
          v-for="prompt in prompts"
          :key="prompt.id"
          class="hover:ring hover:ring-primary transition cursor-pointer"
          @click="viewPrompt(prompt)"
        >
          <template #header>
            <div class="flex flex-col gap-1 items-start justify-between">
              <div class="flex justify-between items-center w-full">
                <h3 class="text-lg  font-medium text-neutral-900 truncate">
                  {{ prompt.name }}
                </h3>
              </div>
              <div class="flex justify-between items-center w-full">
                <p v-if="prompt.category" class="text-sm text-neutral-500 mt-1">
                  {{ prompt.category }}
                </p>
                <div class="text-xs flex items-center text-neutral-500">
                  <UIcon name="i-lucide-calendar" class="inline-block mr-1" />
                  {{ formatDate(prompt.created_at) }}
                </div>
              </div>
            </div>
          </template>

          <div class="space-y-4">
            <p v-if="prompt.description" class="text-sm text-neutral-600">
              {{ prompt.description }}
            </p>
          </div>
        </UCard>
      </div>

      <!-- Create Prompt Modal -->
      <UModal v-model:open="showCreateModal" :prevent-close="creating">
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
                  v-model="newPrompt.name"
                  placeholder="e.g., Language Evaluator"
                  class="w-full"
                  required
                />
              </UFormField>

              <UFormField label="Category">
                <UInput
                  v-model="newPrompt.category"
                  placeholder="e.g., evaluation, generation, analysis"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Description">
                <UTextarea
                  v-model="newPrompt.description"
                  placeholder="Describe what this prompt is used for..."
                  class="w-full"
                  :rows="3"
                />
              </UFormField>

              <div class="flex justify-end gap-2 pt-4 border-t border-neutral-200">
                <UButton
                  type="button"
                  variant="outline"
                  :disabled="creating"
                  @click="showCreateModal = false"
                >
                  Cancel
                </UButton>
                <UButton
                  type="submit"
                  :loading="creating"
                  :disabled="!newPrompt.name.trim() || creating"
                >
                  Create Prompt
                </UButton>
              </div>
            </form>
          </UCard>
        </template>
      </UModal>
    </div>
  </div>
</template>
