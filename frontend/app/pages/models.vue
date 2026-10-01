<script setup lang="ts">
import type { Model } from '~/types'

// Page meta
definePageMeta({
  title: 'Models',
  subtitle: 'Manage available AI models for your experiments',
})

// Fetch data directly in the page
const { data: models, pending, error, refresh } = await useMyLazyFetch<Model[]>('/models')

const availableProviders = computed(() => [...new Set((models.value ?? []).map(m => m.provider))].sort())

// Composables
const { createModel, updateModel, deleteModel: deleteModelApi, toggleModelStatus: toggleStatus } = useModels()
const { selectedProviders, searchQuery, filterModels, toggleProvider, updateSearch, clearFilters } = useModelFilters()
const { showCreateSuccess, showUpdateSuccess, showDeleteSuccess, showCreateError, showUpdateError, showDeleteError } = useStandardToast()

// Page meta
useSeoMeta({
  title: 'Models',
  description: 'Manage available AI models for your experiments.',
})

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
  max_tokens: null as number | null,
  default_temperature: null as number | null,
  default_max_tokens: null as number | null,
  is_active: true,
})

const editForm = ref({
  name: '',
  provider: '',
  description: '',
  max_tokens: null as number | null,
  default_temperature: null as number | null,
  default_max_tokens: null as number | null,
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

const createFormValid = computed(() => {
  return createForm.value.name.trim() && createForm.value.provider.trim()
})

const editFormValid = computed(() => {
  return editForm.value.name.trim() && editForm.value.provider.trim()
})

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Model',
  },
  {
    key: 'provider',
    label: 'Provider',
  },
  {
    key: 'description',
    label: 'Description',
  },
  {
    key: 'is_active',
    label: 'Status',
  },

]

const actions = [
  {
    label: 'Edit',
    icon: 'i-lucide-edit',
    variant: 'ghost' as const,
    color: 'neutral' as const,
    handler: (model: Model) => editModel(model),
  },
  {
    label: (model: Model) => model.is_active ? 'Deactivate' : 'Activate',
    icon: 'i-lucide-power',
    variant: 'ghost' as const,
    color: 'neutral' as const,
    handler: (model: Model) => handleToggleStatus(model),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
    handler: (model: Model) => confirmDelete(model),
  },
]

// Methods
function resetCreateForm() {
  createForm.value = {
    name: '',
    provider: '',
    description: '',
    max_tokens: null,
    default_temperature: null,
    default_max_tokens: null,
    is_active: true,
  }
}

function resetEditForm() {
  editForm.value = {
    name: '',
    provider: '',
    description: '',
    max_tokens: null,
    default_temperature: null,
    default_max_tokens: null,
    is_active: true,
  }
}

async function handleCreateModel() {
  if (!createFormValid.value)
    return

  isCreating.value = true
  try {
    // Convert null to undefined for API
    const formData = {
      ...createForm.value,
      max_tokens: createForm.value.max_tokens ?? undefined,
      default_temperature: createForm.value.default_temperature ?? undefined,
      default_max_tokens: createForm.value.default_max_tokens ?? undefined,
    }

    const result = await createModel(formData)
    if (result.success) {
      showCreateSuccess('Model')
      showCreateModal.value = false
      resetCreateForm()
      // Refresh the models list
      await refresh()
    }
    else {
      showCreateError('Model', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    showCreateError('Model', error instanceof Error ? error.message : undefined)
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
    max_tokens: model.max_tokens ?? null,
    default_temperature: model.default_temperature ?? null,
    default_max_tokens: model.default_max_tokens ?? null,
    is_active: model.is_active,
  }
  showEditModal.value = true
}

async function handleUpdateModel() {
  if (!editingModel.value || !editFormValid.value)
    return

  isUpdating.value = true
  try {
    // Convert null to undefined for API
    const formData = {
      ...editForm.value,
      max_tokens: editForm.value.max_tokens ?? undefined,
      default_temperature: editForm.value.default_temperature ?? undefined,
      default_max_tokens: editForm.value.default_max_tokens ?? undefined,
    }

    const result = await updateModel(editingModel.value.id, formData)
    if (result.success) {
      showUpdateSuccess('Model')
      showEditModal.value = false
      editingModel.value = null
      resetEditForm()
      // Refresh the models list
      await refresh()
    }
    else {
      showUpdateError('Model', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    showUpdateError('Model', error instanceof Error ? error.message : undefined)
  }
  finally {
    isUpdating.value = false
  }
}

async function handleToggleStatus(model: Model) {
  try {
    const result = await toggleStatus(model.id)
    if (result.success) {
      // Refresh the models list
      await refresh()
    }
    else {
      showUpdateError('Model status', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    showUpdateError('Model status', error instanceof Error ? error.message : undefined)
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
      showDeleteSuccess('Model')
      showDeleteModal.value = false
      modelToDelete.value = null
      // Refresh the models list
      await refresh()
    }
    else {
      showDeleteError('Model', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    showDeleteError('Model', error instanceof Error ? error.message : undefined)
  }
  finally {
    isDeleting.value = false
  }
}

function handleCreateClick() {
  showCreateModal.value = true
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
  <BasePageContent
    :loading="pending"
    :error="error ? 'Failed to load models' : null"
  >
    <template #before-content>
      <UButton
        color="primary"
        icon="i-lucide-plus"
        size="sm"
        @click="handleCreateClick"
      >
        Add model
      </UButton>
    </template>

    <!-- Filters -->
    <div class="mb-6">
      <ModelsFilters
        :providers="availableProviders"
        :selected-providers="[...selectedProviders]"
        :search-query="searchQuery"
        :total-count="models?.length || 0"
        :filtered-count="filteredModels.length"
        @toggle-provider="toggleProvider"
        @update-search="updateSearch"
        @clear-filters="clearFilters"
      />
    </div>

    <!-- Models Table -->
    <div v-if="filteredModels.length > 0">
      <BaseDataTable
        :data="filteredModels"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        title="All Models"
        @refresh="refresh"
      >
        <!-- Custom cell for status -->
        <template #is_active-cell="{ row }">
          <UBadge
            :color="row.original.is_active ? 'success' : 'neutral'"
            :label="row.original.is_active ? 'Active' : 'Inactive'"
            variant="soft"
          />
        </template>

        <!-- Custom cell for description -->
        <template #description-cell="{ row }">
          <span class="text-sm text-toned">
            {{ row.original.description || 'No description' }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending && (!models || models.length === 0)"
      title="No models yet"
      message="Start by adding your first AI model"
      icon="i-lucide-cpu"
      action-label="Add model"
      @action="handleCreateClick"
    />

    <!-- No Results State -->
    <BaseEmptyState
      v-else-if="!pending && filteredModels.length === 0"
      title="No models match your filters"
      message="Try adjusting your search or filter criteria"
      icon="i-lucide:search-x"
      action-label="Clear filters"
      action-icon="i-lucide-x"
      @action="clearFilters"
    />

    <!-- Create Model Modal -->
    <BaseCrudModal
      v-model:open="showCreateModal"
      title="Model"
      mode="create"
      :loading="isCreating"
      @submit="handleCreateModel"
    >
      <div class="space-y-6">
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
            <label class="text-sm font-medium text-default">Active</label>
            <USwitch
              v-model="createForm.is_active"
            />
          </div>
        </div>
      </div>
    </BaseCrudModal>

    <!-- Edit Model Modal -->
    <BaseCrudModal
      v-model:open="showEditModal"
      title="Model"
      mode="edit"
      :loading="isUpdating"
      @submit="handleUpdateModel"
    >
      <div class="space-y-6">
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
            <label class="text-sm font-medium text-default">Active</label>
            <USwitch
              v-model="editForm.is_active"
            />
          </div>
        </div>
      </div>
    </BaseCrudModal>

    <!-- Delete Confirmation Modal -->
    <BaseConfirmDialog
      v-model:open="showDeleteModal"
      title="Delete Model"
      :message="`Are you sure you want to delete &quot;${modelToDelete?.name}&quot;? This action cannot be undone.`"
      confirm-label="Delete Model"
      variant="error"
      :loading="isDeleting"
      @confirm="handleDeleteModel"
    />
  </BasePageContent>
</template>
