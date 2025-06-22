<script setup lang="ts">
import type { Model } from '~/types'

// Meta
definePageMeta({
  title: 'Models',
})

// Composables
const { models, pending, error, createModel, updateModel, deleteModel: deleteModelApi, toggleModelStatus: toggleStatus } = useModels()
const { selectedProviders, searchQuery, filterModels, toggleProvider, updateSearch, clearFilters } = useModelFilters()

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
  default_temperature: '' as string,
  default_max_tokens: '' as string,
  is_active: true,
})

const editForm = ref({
  name: '',
  provider: '',
  description: '',
  max_tokens: '' as string,
  default_temperature: '' as string,
  default_max_tokens: '' as string,
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
const filteredModels = computed(() => {
  return filterModels(models.value || [])
})

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
    default_temperature: '',
    default_max_tokens: '',
    is_active: true,
  }
}

function resetEditForm() {
  editForm.value = {
    name: '',
    provider: '',
    description: '',
    max_tokens: '',
    default_temperature: '',
    default_max_tokens: '',
    is_active: true,
  }
}

async function handleCreateModel() {
  if (!formValid.value)
    return

  isCreating.value = true
  try {
    // Convert numeric fields to numbers if they exist and are not empty
    const formData = {
      ...createForm.value,
      max_tokens: createForm.value.max_tokens && createForm.value.max_tokens.trim()
        ? Number(createForm.value.max_tokens)
        : undefined,
      default_temperature: createForm.value.default_temperature && createForm.value.default_temperature.trim()
        ? Number(createForm.value.default_temperature)
        : undefined,
      default_max_tokens: createForm.value.default_max_tokens && createForm.value.default_max_tokens.trim()
        ? Number(createForm.value.default_max_tokens)
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
    default_temperature: model.default_temperature ? model.default_temperature.toString() : '',
    default_max_tokens: model.default_max_tokens ? model.default_max_tokens.toString() : '',
    is_active: model.is_active,
  }
  showEditModal.value = true
}

async function handleUpdateModel() {
  if (!editingModel.value || !editFormValid.value)
    return

  isUpdating.value = true
  try {
    // Convert numeric fields to numbers if they exist and are not empty
    const formData = {
      ...editForm.value,
      max_tokens: editForm.value.max_tokens && editForm.value.max_tokens.trim()
        ? Number(editForm.value.max_tokens)
        : undefined,
      default_temperature: editForm.value.default_temperature && editForm.value.default_temperature.trim()
        ? Number(editForm.value.default_temperature)
        : undefined,
      default_max_tokens: editForm.value.default_max_tokens && editForm.value.default_max_tokens.trim()
        ? Number(editForm.value.default_max_tokens)
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
        <h1 class="text-3xl font-bold text-neutral-900">
          AI Models
        </h1>
        <p class="text-neutral-600 mt-2">
          Manage available AI models for your experiments
        </p>
      </div>
      <UButton
        icon="i-heroicons-plus"
        label="Add Model"
        @click="showCreateModal = true"
      />
    </div>

    <!-- Filters -->
    <div class="mb-8">
      <ModelsFilters
        :selected-providers="[...selectedProviders]"
        :search-query="searchQuery"
        :total-count="models?.length || 0"
        :filtered-count="filteredModels.length"
        @toggle-provider="toggleProvider"
        @update-search="updateSearch"
        @clear-filters="clearFilters"
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
      <UIcon name="i-heroicons-cpu-chip" class="w-16 h-16 text-neutral-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-neutral-900 mb-2">
        No models yet
      </h3>
      <p class="text-neutral-600 mb-4">
        Start by adding your first AI model
      </p>
      <UButton
        icon="i-heroicons-plus"
        label="Add Model"
        @click="showCreateModal = true"
      />
    </div>

    <!-- No Results State -->
    <div v-else-if="filteredModels.length === 0" class="text-center py-12">
      <UIcon name="i-heroicons-funnel" class="w-16 h-16 text-neutral-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-neutral-900 mb-2">
        No models match your filters
      </h3>
      <p class="text-neutral-600 mb-4">
        Try adjusting your search or filter criteria
      </p>
      <UButton
        variant="outline"
        label="Clear Filters"
        @click="clearFilters"
      />
    </div>

    <!-- Models Grid -->
    <div v-else>
      <!-- Model Cards -->
      <div class="grid gap-6">
        <ModelsCard
          v-for="model in filteredModels"
          :key="model.id"
          :model="model"
          @edit="editModel"
          @delete="confirmDelete"
          @toggle-status="handleToggleStatus"
        />
      </div>
    </div>

    <!-- Create Model Modal -->
    <UModal v-model:open="showCreateModal" :prevent-close="isCreating">
      <template #content>
        <UCard class="overflow-y-auto">
          <template #header>
            <h2 class="text-lg font-semibold text-neutral-900">
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
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Provider" required>
                <USelect
                  v-model="createForm.provider"
                  :items="providerOptions"
                  placeholder="Select provider"
                  required
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Description">
                <UTextarea
                  v-model="createForm.description"
                  placeholder="Brief description of the model"
                  :rows="3"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Max Tokens">
                <UInput
                  v-model="createForm.max_tokens"
                  type="number"
                  placeholder="e.g., 128000"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Default Temperature">
                <UInput
                  v-model="createForm.default_temperature"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  placeholder="e.g., 0.7"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Default Max Tokens">
                <UInput
                  v-model="createForm.default_max_tokens"
                  type="number"
                  placeholder="e.g., 2048"
                  class="w-full"
                />
              </UFormField>

              <div class="flex items-center justify-between">
                <label class="text-sm font-medium text-neutral-700">Active</label>
                <USwitch
                  v-model="createForm.is_active"
                  name="is_active"
                />
              </div>
            </div>

            <div class="flex gap-3 justify-end pt-4 border-t border-neutral-200">
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
            <h2 class="text-lg font-semibold text-neutral-900">
              Edit Model
            </h2>
          </template>

          <form class="space-y-6" @submit.prevent="handleUpdateModel">
            <div class="grid grid-cols-1 gap-4">
              <UFormField label="Name" required>
                <UInput
                  v-model="editForm.name"
                  required
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Provider" required>
                <USelect
                  v-model="editForm.provider"
                  :items="providerOptions"
                  required
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Description">
                <UTextarea
                  v-model="editForm.description"
                  :rows="3"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Max Tokens">
                <UInput
                  v-model="editForm.max_tokens"
                  type="number"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Default Temperature">
                <UInput
                  v-model="editForm.default_temperature"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  class="w-full"
                />
              </UFormField>

              <UFormField label="Default Max Tokens">
                <UInput
                  v-model="editForm.default_max_tokens"
                  type="number"
                  class="w-full"
                />
              </UFormField>

              <div class="flex items-center justify-between">
                <label class="text-sm font-medium text-neutral-700">Active</label>
                <USwitch
                  v-model="editForm.is_active"
                  name="edit_is_active"
                />
              </div>
            </div>

            <div class="flex gap-3 justify-end pt-4 border-t border-neutral-200">
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
            <p class="text-neutral-700">
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
