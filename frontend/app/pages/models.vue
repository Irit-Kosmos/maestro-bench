<script setup lang="ts">
import type { ModelFormValues } from '~/components/Models/Form.vue'
import type { Model, ProviderStatus } from '~/types'

// Page meta
definePageMeta({
  title: 'Models',
  subtitle: 'Manage available AI models for your experiments',
})

// Fetch data directly in the page
const { data: models, pending, error, refresh } = await useMyLazyFetch<Model[]>('/models')
const { data: providerStatuses } = await useMyLazyFetch<ProviderStatus[]>('/providers')

// Composables
const { createModel, updateModel, deleteModel: deleteModelApi, toggleModelStatus: toggleStatus } = useModels()
const { search, providers, status, groupBy, providerOptions, statusCounts, filtered, groups, hasFilters, isCollapsed, toggleCollapsed, clear: clearFilters } = useModelFilters(models)
const { showCreateSuccess, showUpdateSuccess, showDeleteSuccess, showCreateError, showUpdateError, showDeleteError } = useStandardToast()

// Whether the backend holds an API key for a provider, by canonical key
const providerStatus = computed(() => Object.fromEntries(
  (providerStatuses.value ?? []).map(item => [providerMeta(item.provider).key, item]),
))

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

function emptyForm(): ModelFormValues {
  return {
    name: '',
    provider: '',
    description: '',
    max_tokens: null,
    default_temperature: null,
    default_max_tokens: null,
    is_active: true,
  }
}

const createForm = ref<ModelFormValues>(emptyForm())
const editForm = ref<ModelFormValues>(emptyForm())

// Computed
const createFormValid = computed(() => {
  return createForm.value.name.trim() && createForm.value.provider.trim()
})

const editFormValid = computed(() => {
  return editForm.value.name.trim() && editForm.value.provider.trim()
})

// Methods
function resetCreateForm() {
  createForm.value = emptyForm()
}

function resetEditForm() {
  editForm.value = emptyForm()
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
  // Flip it right away: the switch is used in bursts and shouldn't wait on the network
  model.is_active = !model.is_active
  try {
    const result = await toggleStatus(model.id)
    if (!result.success) {
      model.is_active = !model.is_active
      showUpdateError('Model status', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    model.is_active = !model.is_active
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
    :loading="pending && !models"
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

    <!-- Models -->
    <div v-if="models && models.length > 0" class="overflow-hidden rounded-lg border border-default">
      <ModelsFilters
        v-model:search="search"
        v-model:providers="providers"
        v-model:status="status"
        v-model:group-by="groupBy"
        :provider-options="providerOptions"
        :status-counts="statusCounts"
        :total="models.length"
        :shown="filtered.length"
        :has-filters="hasFilters"
        :loading="pending"
        @clear="clearFilters"
        @refresh="refresh"
      />

      <ModelsList
        v-if="filtered.length > 0"
        :groups="groups"
        :grouped="groupBy !== 'none'"
        :show-provider="groupBy !== 'provider'"
        :is-collapsed="isCollapsed"
        :provider-status="providerStatus"
        @toggle-group="toggleCollapsed"
        @edit="editModel"
        @toggle-status="handleToggleStatus"
        @delete="confirmDelete"
      />

      <!-- No Results State -->
      <div v-else class="p-6">
        <BaseEmptyState
          title="No models match your filters"
          message="Try another search, or clear the filters."
          icon="i-lucide-search-x"
          action-label="Clear filters"
          action-icon="i-lucide-x"
          @action="clearFilters"
        />
      </div>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending"
      title="No models yet"
      message="Start by adding your first AI model"
      icon="i-lucide-cpu"
      action-label="Add model"
      @action="handleCreateClick"
    />

    <!-- Create Model Modal -->
    <BaseCrudModal
      v-model:open="showCreateModal"
      title="Model"
      mode="create"
      :loading="isCreating"
      @submit="handleCreateModel"
    >
      <ModelsForm v-model="createForm" name-placeholder="e.g. gpt-4-turbo" />
    </BaseCrudModal>

    <!-- Edit Model Modal -->
    <BaseCrudModal
      v-model:open="showEditModal"
      title="Model"
      mode="edit"
      :loading="isUpdating"
      @submit="handleUpdateModel"
    >
      <ModelsForm v-model="editForm" />
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
