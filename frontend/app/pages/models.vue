<script setup lang="ts">
import type { Model } from '~/types'

// Meta
definePageMeta({
  title: 'Models',
})

// Composables
const { models, pending, error, createModel, updateModel, deleteModel: deleteModelApi, toggleModelStatus: toggleStatus } = useModels()

// State
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const editingModel = ref<Model | null>(null)
const modelToDelete = ref<Model | null>(null)
const isCreating = ref(false)
const isUpdating = ref(false)
const isDeleting = ref(false)

const createForm = ref({
  name: '',
  provider: '',
  description: '',
  max_tokens: '' as string,
  is_active: true,
})

const editForm = ref({
  name: '',
  provider: '',
  description: '',
  max_tokens: '' as string,
  is_active: true,
})

// Provider options
const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Mistral', value: 'mistral' },
  { label: 'Google', value: 'google' },
  { label: 'Meta', value: 'meta' },
  { label: 'Other', value: 'other' },
]

// Computed
const formValid = computed(() => {
  return createForm.value.name.trim() && createForm.value.provider.trim()
})

const editFormValid = computed(() => {
  return editForm.value.name.trim() && editForm.value.provider.trim()
})

// Methods
function resetCreateForm() {
  createForm.value = {
    name: '',
    provider: '',
    description: '',
    max_tokens: '',
    is_active: true,
  }
}

function resetEditForm() {
  editForm.value = {
    name: '',
    provider: '',
    description: '',
    max_tokens: '',
    is_active: true,
  }
}

async function handleCreateModel() {
  if (!formValid.value)
    return

  isCreating.value = true
  try {
    // Convert max_tokens to number if it exists and is not empty
    const formData = {
      ...createForm.value,
      max_tokens: createForm.value.max_tokens && createForm.value.max_tokens.trim()
        ? Number(createForm.value.max_tokens)
        : undefined,
    }

    const result = await createModel(formData)
    if (result.success) {
      showCreateModal.value = false
      resetCreateForm()
    }
    else {
      console.error('Failed to create model:', result.error)
    }
  }
  catch (error) {
    console.error('Error creating model:', error)
  }
  finally {
    isCreating.value = false
  }
}

function editModel(model: Model) {
  editingModel.value = model
  editForm.value = {
    name: model.name,
    provider: model.provider,
    description: model.description || '',
    max_tokens: model.max_tokens ? model.max_tokens.toString() : '',
    is_active: model.is_active,
  }
  showEditModal.value = true
}

async function handleUpdateModel() {
  if (!editingModel.value || !editFormValid.value)
    return

  isUpdating.value = true
  try {
    // Convert max_tokens to number if it exists and is not empty
    const formData = {
      ...editForm.value,
      max_tokens: editForm.value.max_tokens && editForm.value.max_tokens.trim()
        ? Number(editForm.value.max_tokens)
        : undefined,
    }

    const result = await updateModel(editingModel.value.id, formData)
    if (result.success) {
      showEditModal.value = false
      editingModel.value = null
      resetEditForm()
    }
    else {
      console.error('Failed to update model:', result.error)
    }
  }
  catch (error) {
    console.error('Error updating model:', error)
  }
  finally {
    isUpdating.value = false
  }
}

async function handleToggleStatus(model: Model) {
  try {
    const result = await toggleStatus(model.id)
    if (!result.success) {
      console.error('Failed to toggle model status:', result.error)
    }
  }
  catch (error) {
    console.error('Error toggling model status:', error)
  }
}

function confirmDelete(model: Model) {
  modelToDelete.value = model
  showDeleteModal.value = true
}

async function handleDeleteModel() {
  if (!modelToDelete.value)
    return

  isDeleting.value = true
  try {
    const result = await deleteModelApi(modelToDelete.value.id)
    if (result.success) {
      showDeleteModal.value = false
      modelToDelete.value = null
    }
    else {
      console.error('Failed to delete model:', result.error)
    }
  }
  catch (error) {
    console.error('Error deleting model:', error)
  }
  finally {
    isDeleting.value = false
  }
}

// Watch for modal close to reset forms
watch(() => showCreateModal.value, (newValue) => {
  if (!newValue) {
    resetCreateForm()
  }
})

watch(() => showEditModal.value, (newValue) => {
  if (!newValue) {
    resetEditForm()
    editingModel.value = null
  }
})

watch(() => showDeleteModal.value, (newValue) => {
  if (!newValue) {
    modelToDelete.value = null
  }
})
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">
          AI Models
        </h1>
        <p class="text-gray-600 mt-2">
          Manage available AI models for your experiments
        </p>
      </div>
      <UButton
        icon="i-heroicons-plus"
        label="Add Model"
        @click="showCreateModal = true"
      />
    </div>

    <!-- Loading State -->
    <div v-if="pending" class="flex justify-center py-8">
      <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin text-primary-500" />
    </div>

    <!-- Error State -->
    <UAlert
      v-else-if="error"
      icon="i-heroicons-exclamation-triangle"
      color="error"
      variant="soft"
      title="Failed to load models"
      description="Please try again later."
      class="mb-6"
    />

    <!-- Empty State -->
    <div v-else-if="!models || models.length === 0" class="text-center py-12">
      <UIcon name="i-heroicons-cpu-chip" class="w-16 h-16 text-gray-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-gray-900 mb-2">
        No models yet
      </h3>
      <p class="text-gray-600 mb-4">
        Start by adding your first AI model
      </p>
      <UButton
        icon="i-heroicons-plus"
        label="Add Model"
        @click="showCreateModal = true"
      />
    </div>

    <!-- Models Grid -->
    <div v-else class="grid gap-6">
      <UCard
        v-for="model in models"
        :key="model.id"
        class="hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-xl font-semibold text-gray-900">
                {{ model.name }}
              </h3>
              <UBadge
                :color="model.is_active ? 'success' : 'neutral'"
                variant="soft"
                size="sm"
              >
                {{ model.is_active ? 'Active' : 'Inactive' }}
              </UBadge>
            </div>

            <div class="space-y-2 text-sm text-gray-600">
              <div class="flex items-center gap-2">
                <UIcon name="i-heroicons-building-office" class="w-4 h-4" />
                <span class="font-medium">Provider:</span>
                <span class="capitalize">{{ model.provider }}</span>
              </div>

              <div v-if="model.description" class="flex items-start gap-2">
                <UIcon name="i-heroicons-document-text" class="w-4 h-4 mt-0.5" />
                <span class="font-medium">Description:</span>
                <span>{{ model.description }}</span>
              </div>

              <div v-if="model.max_tokens" class="flex items-center gap-2">
                <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4" />
                <span class="font-medium">Max Tokens:</span>
                <span>{{ model.max_tokens?.toLocaleString() }}</span>
              </div>

              <div class="flex items-center gap-2">
                <UIcon name="i-heroicons-calendar" class="w-4 h-4" />
                <span class="font-medium">Created:</span>
                <span>{{ new Date(model.created_at).toLocaleDateString() }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 ml-4">
            <UButton
              icon="i-heroicons-pencil"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="editModel(model)"
            />

            <UButton
              :icon="model.is_active ? 'i-heroicons-pause' : 'i-heroicons-play'"
              :color="model.is_active ? 'warning' : 'success'"
              variant="ghost"
              size="sm"
              @click="handleToggleStatus(model)"
            />

            <UButton
              icon="i-heroicons-trash"
              color="error"
              variant="ghost"
              size="sm"
              @click="confirmDelete(model)"
            />
          </div>
        </div>
      </UCard>
    </div>

    <!-- Create Model Modal -->
    <UModal v-model:open="showCreateModal" :prevent-close="isCreating">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h2 class="text-lg font-semibold text-gray-900">
              Create New Model
            </h2>
          </template>

          <form class="space-y-6" @submit.prevent="handleCreateModel">
            <div class="grid grid-cols-1 gap-4">
              <UFormField label="Name" required>
                <UInput
                  v-model="createForm.name"
                  placeholder="e.g., gpt-4-turbo"
                  required
                />
              </UFormField>

              <UFormField label="Provider" required>
                <USelect
                  v-model="createForm.provider"
                  :items="providerOptions"
                  placeholder="Select provider"
                  required
                />
              </UFormField>

              <UFormField label="Description">
                <UTextarea
                  v-model="createForm.description"
                  placeholder="Brief description of the model"
                  :rows="3"
                />
              </UFormField>

              <UFormField label="Max Tokens">
                <UInput
                  v-model="createForm.max_tokens"
                  type="number"
                  placeholder="e.g., 128000"
                />
              </UFormField>

              <div class="flex items-center space-x-2">
                <UCheckbox
                  v-model="createForm.is_active"
                  name="is_active"
                />
                <label for="is_active" class="text-sm text-gray-700">Active</label>
              </div>
            </div>

            <div class="flex gap-3 justify-end pt-4 border-t border-gray-200">
              <UButton
                type="button"
                variant="outline"
                color="neutral"
                :disabled="isCreating"
                @click="showCreateModal = false"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                :disabled="!formValid || isCreating"
                :loading="isCreating"
              >
                Create Model
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>

    <!-- Edit Model Modal -->
    <UModal v-model:open="showEditModal" :prevent-close="isUpdating">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h2 class="text-lg font-semibold text-gray-900">
              Edit Model
            </h2>
          </template>

          <form class="space-y-6" @submit.prevent="handleUpdateModel">
            <div class="grid grid-cols-1 gap-4">
              <UFormField label="Name" required>
                <UInput
                  v-model="editForm.name"
                  required
                />
              </UFormField>

              <UFormField label="Provider" required>
                <USelect
                  v-model="editForm.provider"
                  :items="providerOptions"
                  required
                />
              </UFormField>

              <UFormField label="Description">
                <UTextarea
                  v-model="editForm.description"
                  :rows="3"
                />
              </UFormField>

              <UFormField label="Max Tokens">
                <UInput
                  v-model="editForm.max_tokens"
                  type="number"
                />
              </UFormField>

              <div class="flex items-center space-x-2">
                <UCheckbox
                  v-model="editForm.is_active"
                  name="edit_is_active"
                />
                <label for="edit_is_active" class="text-sm text-gray-700">Active</label>
              </div>
            </div>

            <div class="flex gap-3 justify-end pt-4 border-t border-gray-200">
              <UButton
                type="button"
                variant="outline"
                color="neutral"
                :disabled="isUpdating"
                @click="showEditModal = false"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                :disabled="!editFormValid || isUpdating"
                :loading="isUpdating"
              >
                Update Model
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteModal" :prevent-close="isDeleting">
      <template #content>
        <UCard>
          <template #header>
            <h2 class="text-lg font-semibold text-red-600">
              Delete Model
            </h2>
          </template>

          <div class="py-4">
            <p class="text-gray-700">
              Are you sure you want to delete "<strong>{{ modelToDelete?.name }}</strong>"?
              This action cannot be undone.
            </p>
          </div>

          <template #footer>
            <div class="flex justify-end gap-3">
              <UButton
                variant="outline"
                color="neutral"
                :disabled="isDeleting"
                @click="showDeleteModal = false"
              >
                Cancel
              </UButton>
              <UButton
                color="error"
                :disabled="isDeleting"
                :loading="isDeleting"
                @click="handleDeleteModel"
              >
                Delete Model
              </UButton>
            </div>
          </template>
        </UCard>
      </template>
    </UModal>
  </div>
</template>
