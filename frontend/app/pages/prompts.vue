<script setup lang="ts">
import type { Prompt } from '~/types'

// Composables
const { prompts, refresh, pending, error, createPrompt, updatePrompt, deletePrompt } = usePrompts()
const toast = useToast()

// Page meta
useSeoMeta({
  title: 'Prompts',
  description: 'Manage your reusable prompts with versioning support',
})

// State
const showCreateModal = ref(false)
const showEditModal = ref(false)
const creating = ref(false)
const updating = ref(false)

const newPrompt = ref({
  name: '',
  description: '',
  category: '',
})

const editPrompt = ref({
  id: 0,
  name: '',
  description: '',
  category: '',
})

// Methods
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}

function getPromptActions(prompt: Prompt) {
  return [
    [{
      label: 'Edit',
      icon: 'i-lucide-edit',
      click: () => openEditModal(prompt),
    }],
    [{
      label: 'Delete',
      icon: 'i-lucide-trash-2',
      click: () => handleDeletePrompt(prompt.id),
    }],
  ]
}

function viewPrompt(prompt: Prompt) {
  navigateTo(`/prompts/${prompt.id}`)
}

function manageVersions(prompt: Prompt) {
  navigateTo(`/prompts/${prompt.id}/versions`)
}

function openEditModal(prompt: Prompt) {
  editPrompt.value = {
    id: prompt.id,
    name: prompt.name,
    description: prompt.description || '',
    category: prompt.category || '',
  }
  showEditModal.value = true
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

async function handleEditPrompt() {
  updating.value = true
  try {
    const result = await updatePrompt(editPrompt.value.id, {
      name: editPrompt.value.name,
      description: editPrompt.value.description || undefined,
      category: editPrompt.value.category || undefined,
    })

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Prompt updated successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      showEditModal.value = false
    }
    else {
      toast.add({
        title: 'Error',
        description: result.error || 'Failed to update prompt',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch {
    toast.add({
      title: 'Error',
      description: 'Error updating prompt. Please try again.',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    updating.value = false
  }
}

async function handleDeletePrompt(promptId: number) {
  // TODO: Add proper confirmation dialog
  const result = await deletePrompt(promptId)
  if (result.success) {
    toast.add({
      title: 'Success',
      description: 'Prompt deleted successfully!',
      color: 'success',
      icon: 'i-lucide:check-circle',
    })
  }
  else {
    toast.add({
      title: 'Error',
      description: result.error || 'Failed to delete prompt',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Page Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            Prompts
          </h1>
          <p class="text-gray-500 mt-1">
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
        <USpinner size="lg" />
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-12">
        <UIcon name="i-lucide-alert-circle" class="h-16 w-16 text-red-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          Error Loading Prompts
        </h3>
        <p class="text-gray-600 mb-4">
          {{ error }}
        </p>
        <UButton @click="() => refresh()">
          Try Again
        </UButton>
      </div>

      <!-- Empty State -->
      <div v-else-if="!prompts || prompts.length === 0" class="text-center py-12">
        <UIcon name="i-lucide-message-square-text" class="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          No Prompts Found
        </h3>
        <p class="text-gray-600 mb-6">
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
          class="hover:shadow-lg transition-shadow duration-200"
        >
          <template #header>
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <h3 class="text-lg font-medium text-gray-900 truncate">
                  {{ prompt.name }}
                </h3>
                <p v-if="prompt.category" class="text-sm text-gray-500 mt-1">
                  {{ prompt.category }}
                </p>
              </div>
              <UDropdown :items="getPromptActions(prompt)">
                <UButton
                  icon="i-lucide-more-vertical"
                  variant="ghost"
                  size="sm"
                />
              </UDropdown>
            </div>
          </template>

          <div class="space-y-4">
            <p v-if="prompt.description" class="text-sm text-gray-600">
              {{ prompt.description }}
            </p>

            <div class="flex items-center justify-between">
              <div class="text-xs text-gray-500">
                Created {{ formatDate(prompt.created_at) }}
              </div>
              <UBadge variant="subtle" color="primary">
                {{ prompt.versions?.length || 0 }} version{{ (prompt.versions?.length || 0) !== 1 ? 's' : '' }}
              </UBadge>
            </div>

            <div class="flex gap-2">
              <UButton
                variant="outline"
                size="sm"
                icon="i-lucide-eye"
                @click="viewPrompt(prompt)"
              >
                View
              </UButton>
              <UButton
                variant="outline"
                size="sm"
                icon="i-lucide-git-branch"
                @click="manageVersions(prompt)"
              >
                Versions
              </UButton>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Create Prompt Modal -->
      <UModal v-model="showCreateModal">
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">
              Create New Prompt
            </h3>
          </template>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Prompt Name *
              </label>
              <UInput
                v-model="newPrompt.name"
                placeholder="e.g., Language Evaluator"
                required
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <UInput
                v-model="newPrompt.category"
                placeholder="e.g., evaluation, generation, analysis"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <UTextarea
                v-model="newPrompt.description"
                placeholder="Describe what this prompt is used for..."
                :rows="3"
              />
            </div>
          </div>

          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton
                variant="outline"
                @click="showCreateModal = false"
              >
                Cancel
              </UButton>
              <UButton
                :loading="creating"
                @click="handleCreatePrompt"
              >
                Create Prompt
              </UButton>
            </div>
          </template>
        </UCard>
      </UModal>

      <!-- Edit Prompt Modal -->
      <UModal v-model="showEditModal">
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">
              Edit Prompt
            </h3>
          </template>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Prompt Name *
              </label>
              <UInput
                v-model="editPrompt.name"
                required
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <UInput
                v-model="editPrompt.category"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <UTextarea
                v-model="editPrompt.description"
                :rows="3"
              />
            </div>
          </div>

          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton
                variant="outline"
                @click="showEditModal = false"
              >
                Cancel
              </UButton>
              <UButton
                :loading="updating"
                @click="handleEditPrompt"
              >
                Update Prompt
              </UButton>
            </div>
          </template>
        </UCard>
      </UModal>
    </div>
  </div>
</template>
