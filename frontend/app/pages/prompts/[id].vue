<script setup lang="ts">
import type { Prompt, PromptVersion } from '~/types'

// Route params
const route = useRoute()
const promptId = Number.parseInt(route.params.id as string)

// Composables
const { updatePrompt, getPromptVersions, createPromptVersion, deletePromptVersion } = usePrompts()
const toast = useToast()

// Fetch prompt details
const { data: prompt, refresh, pending, error } = await useMyLazyFetch<Prompt>(`/prompts/${promptId}`)

// Page meta
useSeoMeta({
  title: computed(() => prompt.value ? `${prompt.value.name} - Prompts` : 'Prompt Details'),
  description: computed(() => prompt.value?.description || 'View and manage prompt versions'),
})

// State
const showEditPromptModal = ref(false)
const showCreateVersionModal = ref(false)
const updatingPrompt = ref(false)
const creatingVersion = ref(false)
const versionsLoading = ref(false)
const versions = ref<PromptVersion[]>([])

// Form data
const editPromptData = ref({
  name: '',
  description: '',
  category: '',
})

const newVersionData = ref({
  version: '',
  system_prompt: '',
  user_prompt: '',
  variables: '',
  is_active: true,
  is_default: false,
  notes: '',
})

// Watch for prompt changes to update edit form
watch(prompt, (newPrompt) => {
  if (newPrompt) {
    editPromptData.value = {
      name: newPrompt.name,
      description: newPrompt.description || '',
      category: newPrompt.category || '',
    }
    loadVersions()
  }
}, { immediate: true })

// Methods
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}

async function loadVersions() {
  versionsLoading.value = true
  try {
    const result = await getPromptVersions(promptId)
    if (result.success) {
      versions.value = (result.data as PromptVersion[]) || []
    }
  }
  catch {
    console.error('Error loading versions')
  }
  finally {
    versionsLoading.value = false
  }
}

function getVersionActions(version: PromptVersion) {
  return [
    [{
      label: 'Edit',
      icon: 'i-lucide-edit',
      click: () => editVersion(version),
    }],
    [{
      label: 'Delete',
      icon: 'i-lucide-trash-2',
      click: () => deleteVersion(version.id),
    }],
  ]
}

async function handleEditPrompt() {
  updatingPrompt.value = true
  try {
    const result = await updatePrompt(promptId, editPromptData.value)

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Prompt updated successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      showEditPromptModal.value = false
      await refresh()
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
      description: 'An unexpected error occurred',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    updatingPrompt.value = false
  }
}

async function handleCreateVersion() {
  creatingVersion.value = true
  try {
    const versionData = {
      ...newVersionData.value,
      system_prompt: newVersionData.value.system_prompt || undefined,
      user_prompt: newVersionData.value.user_prompt || undefined,
      variables: newVersionData.value.variables || undefined,
      notes: newVersionData.value.notes || undefined,
    }

    const result = await createPromptVersion(promptId, versionData)

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Version created successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      showCreateVersionModal.value = false
      resetVersionForm()
      await loadVersions()
    }
    else {
      toast.add({
        title: 'Error',
        description: result.error || 'Failed to create version',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch {
    toast.add({
      title: 'Error',
      description: 'An unexpected error occurred',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    creatingVersion.value = false
  }
}

function resetVersionForm() {
  newVersionData.value = {
    version: '',
    system_prompt: '',
    user_prompt: '',
    variables: '',
    is_active: true,
    is_default: false,
    notes: '',
  }
}

function editVersion(_version: PromptVersion) {
  // TODO: Implement version editing
  toast.add({
    title: 'Coming Soon',
    description: 'Version editing will be available soon',
    color: 'info',
    icon: 'i-lucide:info',
  })
}

async function deleteVersion(versionId: number) {
  try {
    const result = await deletePromptVersion(versionId)

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Version deleted successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      await loadVersions()
    }
    else {
      toast.add({
        title: 'Error',
        description: result.error || 'Failed to delete version',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch {
    toast.add({
      title: 'Error',
      description: 'An unexpected error occurred',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading state -->
      <div v-if="pending" class="flex justify-center py-12">
        <USkeleton class="h-8 w-8 rounded-full" />
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="text-center py-12">
        <UIcon name="i-lucide-alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 class="text-xl font-semibold text-gray-900 mb-2">
          Error Loading Prompt
        </h2>
        <p class="text-gray-600 mb-4">
          Unable to load prompt details. Please try again.
        </p>
        <UButton variant="outline" @click="() => refresh()">
          Retry
        </UButton>
      </div>

      <!-- Main content -->
      <div v-else-if="prompt">
        <!-- Page Header -->
        <div class="flex justify-between items-center mb-8">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">
              {{ prompt.name }}
            </h1>
            <p class="text-gray-500 mt-1">
              {{ prompt.description || 'Manage versions and configurations for this prompt' }}
            </p>
          </div>
          <div class="flex items-center space-x-3">
            <UButton
              variant="outline"
              icon="i-lucide-edit"
              @click="showEditPromptModal = true"
            >
              Edit Prompt
            </UButton>
            <UButton
              variant="solid"
              color="primary"
              icon="i-lucide-plus"
              @click="showCreateVersionModal = true"
            >
              New Version
            </UButton>
          </div>
        </div>

        <!-- Versions Section -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-xl font-semibold text-gray-900">
              Prompt Versions
            </h2>
            <p class="text-gray-600 text-sm mt-1">
              Manage different versions of this prompt with their configurations
            </p>
          </div>

          <div class="p-6">
            <!-- Loading versions -->
            <div v-if="versionsLoading" class="flex justify-center py-8">
              <USkeleton class="h-6 w-6 rounded-full" />
            </div>

            <!-- No versions -->
            <div v-else-if="!versions || versions.length === 0" class="text-center py-8">
              <UIcon name="i-lucide-file-text" class="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-gray-900 mb-2">
                No versions yet
              </h3>
              <p class="text-gray-600 mb-4">
                Create the first version of this prompt to get started.
              </p>
              <UButton
                variant="solid"
                color="primary"
                icon="i-lucide-plus"
                @click="showCreateVersionModal = true"
              >
                Create First Version
              </UButton>
            </div>

            <!-- Versions list -->
            <div v-else class="space-y-4">
              <div
                v-for="version in versions"
                :key="version.id"
                class="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
              >
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <div class="flex items-center space-x-3 mb-3">
                      <h3 class="text-lg font-medium text-gray-900">
                        Version {{ version.version }}
                      </h3>
                      <UBadge
                        v-if="version.is_default"
                        label="Default"
                        color="success"
                      />
                      <UBadge
                        v-if="!version.is_active"
                        label="Inactive"
                        color="error"
                        variant="subtle"
                      />
                    </div>

                    <!-- Version details grid -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <!-- System Prompt -->
                      <div v-if="version.system_prompt">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                          System Prompt
                        </label>
                        <div class="bg-gray-50 rounded-md p-3 text-sm text-gray-800 font-mono max-h-32 overflow-y-auto">
                          {{ version.system_prompt }}
                        </div>
                      </div>

                      <!-- User Prompt -->
                      <div v-if="version.user_prompt">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                          User Prompt
                        </label>
                        <div class="bg-gray-50 rounded-md p-3 text-sm text-gray-800 font-mono max-h-32 overflow-y-auto">
                          {{ version.user_prompt }}
                        </div>
                      </div>

                      <!-- Variables -->
                      <div v-if="version.variables">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                          Variables
                        </label>
                        <div class="bg-gray-50 rounded-md p-3 text-sm text-gray-800 font-mono max-h-32 overflow-y-auto">
                          {{ version.variables }}
                        </div>
                      </div>
                    </div>

                    <!-- Notes -->
                    <div v-if="version.notes" class="mt-4">
                      <label class="block text-sm font-medium text-gray-700 mb-2">
                        Notes
                      </label>
                      <p class="text-sm text-gray-600">
                        {{ version.notes }}
                      </p>
                    </div>

                    <!-- Meta info -->
                    <div class="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                      <span class="text-xs text-gray-500">
                        Created {{ formatDate(version.created_at) }}
                      </span>
                    </div>
                  </div>

                  <!-- Actions -->
                  <UDropdownMenu :items="getVersionActions(version)">
                    <UButton
                      icon="i-lucide-more-horizontal"
                      variant="ghost"
                      color="neutral"
                    />
                  </UDropdownMenu>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Prompt Modal -->
    <UModal v-model:open="showEditPromptModal" :prevent-close="updatingPrompt">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h3 class="text-lg font-semibold">
              Edit Prompt
            </h3>
          </template>

          <form class="space-y-4" @submit.prevent="handleEditPrompt">
            <UFormField label="Name" required>
              <UInput
                v-model="editPromptData.name"
                placeholder="Enter prompt name"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Description">
              <UTextarea
                v-model="editPromptData.description"
                placeholder="Enter prompt description"
                class="w-full"
                :rows="3"
              />
            </UFormField>

            <UFormField label="Category">
              <UInput
                v-model="editPromptData.category"
                placeholder="Enter category (e.g., evaluation, instruction)"
                class="w-full"
              />
            </UFormField>

            <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
              <UButton
                type="button"
                variant="outline"
                :disabled="updatingPrompt"
                @click="showEditPromptModal = false"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                variant="solid"
                color="primary"
                :loading="updatingPrompt"
                :disabled="!editPromptData.name.trim() || updatingPrompt"
              >
                Update Prompt
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>

    <!-- Create Version Modal -->
    <UModal v-model:open="showCreateVersionModal" :prevent-close="creatingVersion">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h3 class="text-lg font-semibold">
              Create New Version
            </h3>
          </template>

          <form class="space-y-4" @submit.prevent="handleCreateVersion">
            <UFormField label="Version" required>
              <UInput
                v-model="newVersionData.version"
                placeholder="e.g., 1.0, 2.1, v3-beta"
                class="w-full"
              />
            </UFormField>

            <UFormField label="System Prompt">
              <UTextarea
                v-model="newVersionData.system_prompt"
                placeholder="Enter system prompt instructions"
                class="w-full"
                :rows="4"
              />
            </UFormField>

            <UFormField label="User Prompt">
              <UTextarea
                v-model="newVersionData.user_prompt"
                placeholder="Enter user prompt template"
                class="w-full"
                :rows="4"
              />
            </UFormField>

            <UFormField label="Variables">
              <UTextarea
                v-model="newVersionData.variables"
                placeholder="JSON object with variable definitions"
                class="w-full"
                :rows="3"
              />
            </UFormField>

            <UFormField label="Notes">
              <UTextarea
                v-model="newVersionData.notes"
                placeholder="Optional notes about this version"
                class="w-full"
                :rows="3"
              />
            </UFormField>

            <div class="flex items-center space-x-4">
              <UCheckbox
                v-model="newVersionData.is_active"
                label="Active"
              />
              <UCheckbox
                v-model="newVersionData.is_default"
                label="Set as default"
              />
            </div>

            <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
              <UButton
                type="button"
                variant="outline"
                :disabled="creatingVersion"
                @click="showCreateVersionModal = false"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                variant="solid"
                color="primary"
                :loading="creatingVersion"
                :disabled="!newVersionData.version.trim() || creatingVersion"
              >
                Create Version
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>
  </div>
</template>
