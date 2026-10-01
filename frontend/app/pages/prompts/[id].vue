<script setup lang="ts">
import type { Prompt, PromptVersion } from '~/types'

// Route params
const route = useRoute()
const promptId = Number.parseInt(route.params.id as string)

// Composables
const { updatePrompt, getPromptVersions, createPromptVersion, updatePromptVersion, deletePromptVersion } = usePrompts()
const toast = useToast()

// Fetch prompt details
const { data: prompt, refresh, pending, error } = await useMyLazyFetch<Prompt>(`/prompts/${promptId}`)

useBreadcrumbLabel(() => prompt.value?.name)

// Page meta
useSeoMeta({
  title: computed(() => prompt.value ? `${prompt.value.name} - Prompts` : 'Prompt Details'),
  description: computed(() => prompt.value?.description || 'View and manage prompt versions'),
})

// State
const showEditPromptModal = ref(false)
const showCreateVersionModal = ref(false)
const showEditVersionModal = ref(false)
const showDeleteConfirmModal = ref(false)
const updatingPrompt = ref(false)
const creatingVersion = ref(false)
const updatingVersion = ref(false)
const versionsLoading = ref(false)
const versions = ref<PromptVersion[]>([])
const selectedVersionForEdit = ref<PromptVersion | null>(null)
const selectedVersionForDelete = ref<PromptVersion | null>(null)

// Computed property for sorted versions: default first, then by creation date DESC
const sortedVersions = computed(() => {
  if (!versions.value)
    return []

  return [...versions.value].sort((a, b) => {
    // Default version comes first
    if (a.is_default && !b.is_default)
      return -1
    if (!a.is_default && b.is_default)
      return 1

    // Then sort by creation date (most recent first)
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
})

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

const editVersionData = ref({
  version: '',
  system_prompt: '',
  user_prompt: '',
  variables: '',
  is_active: true,
  is_default: false,
  notes: '',
})

// Computed properties for handling variables conversion
const editVersionVariablesArray = computed({
  get: () => parseVariables(editVersionData.value.variables),
  set: (value: string[]) => {
    editVersionData.value.variables = stringifyVariables(value)
  },
})

const newVersionVariablesArray = computed({
  get: () => parseVariables(newVersionData.value.variables),
  set: (value: string[]) => {
    newVersionData.value.variables = stringifyVariables(value)
  },
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

function resetEditVersionForm() {
  editVersionData.value = {
    version: '',
    system_prompt: '',
    user_prompt: '',
    variables: '',
    is_active: true,
    is_default: false,
    notes: '',
  }
}

function openEditVersion(version: PromptVersion) {
  selectedVersionForEdit.value = version
  editVersionData.value = {
    version: version.version,
    system_prompt: version.system_prompt || '',
    user_prompt: version.user_prompt || '',
    variables: version.variables || '',
    is_active: version.is_active,
    is_default: version.is_default,
    notes: version.notes || '',
  }
  showEditVersionModal.value = true
}

async function handleEditVersion() {
  if (!selectedVersionForEdit.value)
    return

  updatingVersion.value = true
  try {
    const versionData = {
      ...editVersionData.value,
      system_prompt: editVersionData.value.system_prompt || undefined,
      user_prompt: editVersionData.value.user_prompt || undefined,
      variables: editVersionData.value.variables || undefined,
      notes: editVersionData.value.notes || undefined,
    }

    const result = await updatePromptVersion(selectedVersionForEdit.value.id, versionData)

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Version updated successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      showEditVersionModal.value = false
      resetEditVersionForm()
      selectedVersionForEdit.value = null
      await loadVersions()
    }
    else {
      toast.add({
        title: 'Error',
        description: result.error || 'Failed to update version',
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
    updatingVersion.value = false
  }
}

function openDeleteConfirm(version: PromptVersion) {
  selectedVersionForDelete.value = version
  showDeleteConfirmModal.value = true
}

async function confirmDeleteVersion() {
  if (!selectedVersionForDelete.value)
    return

  try {
    const result = await deletePromptVersion(selectedVersionForDelete.value.id)

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
  finally {
    showDeleteConfirmModal.value = false
    selectedVersionForDelete.value = null
  }
}

function editVersion(version: PromptVersion) {
  openEditVersion(version)
}

async function deleteVersion(versionId: number) {
  const version = versions.value.find(v => v.id === versionId)
  if (version) {
    openDeleteConfirm(version)
  }
}
</script>

<template>
  <div class="min-h-screen">
    <div>
      <!-- Loading state -->
      <BaseLoadingState v-if="pending" />

      <!-- Error state -->
      <div v-else-if="error" class="text-center py-12">
        <UIcon name="i-lucide-alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 class="text-xl font-semibold text-neutral-900 mb-2">
          Error Loading Prompt
        </h2>
        <p class="text-neutral-600 mb-4">
          Unable to load prompt details. Please try again.
        </p>
        <UButton variant="outline" @click="() => refresh()">
          Retry
        </UButton>
      </div>

      <!-- Main content -->
      <div v-else-if="prompt">
        <AppPageActions>
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-pencil"
            size="sm"
            @click="() => { showEditPromptModal = true }"
          >
            Edit
          </UButton>
          <UButton
            color="primary"
            icon="i-lucide-plus"
            size="sm"
            @click="() => { showCreateVersionModal = true }"
          >
            New version
          </UButton>
        </AppPageActions>

        <div class="mb-6">
          <h1 class="text-xl font-semibold text-highlighted text-balance">
            {{ prompt.name }}
          </h1>
          <p v-if="prompt.description" class="mt-0.5 text-sm text-muted max-w-prose">
            {{ prompt.description }}
          </p>
        </div>

        <!-- Versions Section -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-neutral-200">
            <h2 class="text-xl font-semibold text-neutral-900">
              Prompt Versions
            </h2>
            <p class="text-neutral-600 text-sm mt-1">
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
              <UIcon name="i-lucide-file-text" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-neutral-900 mb-2">
                No versions yet
              </h3>
              <p class="text-neutral-600 mb-4">
                Create the first version of this prompt to get started.
              </p>
              <UButton
                variant="solid"
                color="primary"
                icon="i-lucide-plus"
                @click="() => { showCreateVersionModal = true }"
              >
                Create First Version
              </UButton>
            </div>

            <!-- Versions list -->
            <div v-else class="space-y-4">
              <UCollapsible
                v-for="version in sortedVersions"
                :key="version.id"
                class="border border-neutral-200 rounded-lg overflow-hidden"
                :default-open="version.is_default"
              >
                <!-- Collapsible Header -->
                <UButton
                  class="w-full group p-6 text-left border-0 bg-white hover:bg-neutral-50"
                  variant="ghost"
                  :ui="{
                    base: 'justify-between items-center',
                    trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
                  }"
                  trailing-icon="i-lucide-chevron-down"
                  block
                >
                  <PromptVersionHeader
                    :version="version.version"
                    :is-default="version.is_default"
                    :is-active="version.is_active"
                    :created-at="version.created_at"
                  />
                </UButton>

                <!-- Collapsible Content -->
                <template #content>
                  <div class="px-6 pb-6 bg-neutral-50/50">
                    <!-- Action Buttons -->
                    <div class="flex justify-end space-x-3 mb-6 pt-4 border-b border-neutral-200 pb-4">
                      <UButton
                        variant="outline"
                        size="sm"
                        icon="i-lucide-edit"
                        @click="editVersion(version)"
                      >
                        Edit Version
                      </UButton>
                      <UButton
                        variant="outline"
                        color="error"
                        size="sm"
                        icon="i-lucide-trash-2"
                        @click="deleteVersion(version.id)"
                      >
                        Delete Version
                      </UButton>
                    </div>

                    <div class="space-y-6">
                      <!-- Use shared PromptVersionDetails component -->
                      <PromptVersionDetails
                        :prompt-version="version"
                        :show-header="false"
                        :show-metadata="false"
                      />
                    </div>
                  </div>
                </template>
              </UCollapsible>
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

            <div class="flex justify-end space-x-3 pt-4 border-t border-neutral-200">
              <UButton
                type="button"
                variant="outline"
                :disabled="updatingPrompt"
                @click="() => { showEditPromptModal = false }"
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
                :rows="3"
              />
            </UFormField>

            <UFormField label="User Prompt">
              <UTextarea
                v-model="newVersionData.user_prompt"
                placeholder="Enter user prompt template"
                class="w-full"
                :rows="6"
              />
            </UFormField>

            <UFormField label="Variables">
              <PromptVariablesDisplay
                v-model="newVersionVariablesArray"
                :variables="newVersionData.variables"
                editable
                class="w-full"
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

            <div class="flex justify-end space-x-3 pt-4 border-t border-neutral-200">
              <UButton
                type="button"
                variant="outline"
                :disabled="creatingVersion"
                @click="() => { showCreateVersionModal = false }"
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

    <!-- Edit Version Modal -->
    <UModal v-model:open="showEditVersionModal" :prevent-close="updatingVersion">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h3 class="text-lg font-semibold">
              Edit Version {{ selectedVersionForEdit?.version }}
            </h3>
          </template>

          <form class="space-y-4" @submit.prevent="handleEditVersion">
            <UFormField label="Version" required>
              <UInput
                v-model="editVersionData.version"
                placeholder="e.g., 1.0, 2.1, v3-beta"
                class="w-full"
              />
            </UFormField>

            <UFormField label="System Prompt">
              <UTextarea
                v-model="editVersionData.system_prompt"
                placeholder="Enter system prompt instructions"
                class="w-full"
                :rows="3"
              />
            </UFormField>

            <UFormField label="User Prompt">
              <UTextarea
                v-model="editVersionData.user_prompt"
                placeholder="Enter user prompt template"
                class="w-full"
                :rows="6"
              />
            </UFormField>

            <UFormField label="Variables">
              <PromptVariablesDisplay
                v-model="editVersionVariablesArray"
                :variables="editVersionData.variables"
                editable
                class="w-full"
              />
            </UFormField>

            <UFormField label="Notes">
              <UTextarea
                v-model="editVersionData.notes"
                placeholder="Optional notes about this version"
                class="w-full"
                :rows="3"
              />
            </UFormField>

            <div class="flex items-center space-x-4">
              <UCheckbox
                v-model="editVersionData.is_active"
                label="Active"
              />
              <UCheckbox
                v-model="editVersionData.is_default"
                label="Set as default"
              />
            </div>

            <div class="flex justify-end space-x-3 pt-4 border-t border-neutral-200">
              <UButton
                type="button"
                variant="outline"
                :disabled="updatingVersion"
                @click="() => { showEditVersionModal = false }"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                variant="solid"
                color="primary"
                :loading="updatingVersion"
                :disabled="!editVersionData.version.trim() || updatingVersion"
              >
                Update Version
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteConfirmModal">
      <template #content>
        <UCard>
          <template #header>
            <div class="flex items-center space-x-3">
              <UIcon name="i-lucide-alert-triangle" class="w-6 h-6 text-red-500" />
              <h3 class="text-lg font-semibold text-neutral-900">
                Confirm Delete
              </h3>
            </div>
          </template>

          <div class="space-y-4">
            <p class="text-neutral-600">
              Are you sure you want to delete version <strong>{{ selectedVersionForDelete?.version }}</strong>?
            </p>
            <p class="text-sm text-red-600">
              This action cannot be undone.
            </p>
          </div>

          <template #footer>
            <div class="flex justify-end space-x-3">
              <UButton
                variant="outline"
                @click="() => { showDeleteConfirmModal = false }"
              >
                Cancel
              </UButton>
              <UButton
                variant="solid"
                color="error"
                @click="confirmDeleteVersion"
              >
                Delete Version
              </UButton>
            </div>
          </template>
        </UCard>
      </template>
    </UModal>
  </div>
</template>
