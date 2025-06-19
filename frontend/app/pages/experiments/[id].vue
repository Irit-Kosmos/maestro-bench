<script setup lang="ts">
import type { Experiment } from '~/types'

// Route params
const route = useRoute()
const experimentId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const toast = useToast()
const { fetchExperiment, deleteExperiment } = useExperiments()
const { formatDuration } = useUIHelpers()

// State
const experiment = ref<Experiment | null>(null)
const loading = ref(true)
const showDeleteDialog = ref(false)
const isDeleting = ref(false)

// Computed
const pageTitle = computed(() => {
  return experiment.value ? experiment.value.name : 'Loading...'
})

// Set page title and meta
useSeoMeta({
  title: pageTitle,
  description: computed(() =>
    experiment.value
      ? `View details and results for experiment: ${experiment.value.name}`
      : 'Loading experiment...',
  ),
})

const statusColor = computed(() => {
  if (!experiment.value)
    return 'neutral'
  switch (experiment.value.status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'error'
    case 'pending': return 'warning'
    default: return 'neutral'
  }
})

// Methods
async function loadExperiment() {
  loading.value = true
  try {
    const result = await fetchExperiment(experimentId.value)
    if (result.success && result.data) {
      experiment.value = result.data as Experiment
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Experiment not found',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
      await navigateTo('/experiments')
    }
  }
  catch (error) {
    console.error('Error loading experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load experiment',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
    await navigateTo('/experiments')
  }
  finally {
    loading.value = false
  }
}

async function handleDeleteExperiment() {
  if (!experiment.value)
    return

  isDeleting.value = true
  try {
    const result = await deleteExperiment(experiment.value.id)
    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Experiment deleted successfully',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      await navigateTo('/experiments')
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Failed to delete experiment',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch (error) {
    console.error('Error deleting experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to delete experiment',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    isDeleting.value = false
    showDeleteDialog.value = false
  }
}

const duration = computed(() => {
  return experiment.value
    ? formatDuration(
        experiment.value.completed_at
          ? new Date(experiment.value.completed_at).getTime() / 1000
          - new Date(experiment.value.created_at).getTime() / 1000
          : 0,
      )
    : 'N/A'
})

// Lifecycle
onMounted(() => {
  loadExperiment()
})

// Watch for route changes
watch(() => route.params.id, () => {
  loadExperiment()
})
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
      </div>

      <!-- Experiment Details -->
      <div v-else-if="experiment" class="space-y-8">
        <!-- Header with Actions -->
        <div class="flex justify-between items-center">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">
              {{ experiment.name }}
            </h1>
            <p class="text-gray-500 mt-1">
              Experiment ID: {{ experiment.id }}
            </p>
          </div>
          <div class="flex gap-3">
            <UButton
              variant="outline"
              color="neutral"
              icon="i-lucide:arrow-left"
              @click="$router.go(-1)"
            >
              Back
            </UButton>
            <UButton
              variant="outline"
              color="error"
              icon="i-lucide:trash-2"
              @click="showDeleteDialog = true"
            >
              Delete
            </UButton>
          </div>
        </div>

        <!-- Overview Card -->
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-semibold text-gray-900">
                Experiment Overview
              </h2>
              <UBadge
                :color="statusColor"
                variant="subtle"
                class="capitalize"
              >
                {{ experiment.status }}
              </UBadge>
            </div>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <dt class="text-sm font-medium text-gray-500">
                Created
              </dt>
              <dd class="mt-1 text-sm text-gray-900">
                {{ new Date(experiment.created_at).toLocaleDateString() }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">
                Dataset
              </dt>
              <dd class="mt-1 text-sm text-gray-900">
                {{ experiment.dataset?.name || 'Unknown' }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">
                Status
              </dt>
              <dd class="mt-1 text-sm text-gray-900 capitalize">
                {{ experiment.status }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">
                Duration
              </dt>
              <dd class="mt-1 text-sm text-gray-900">
                <!-- TODO: Calculate duration based on timestamps -->
                {{ experiment.status === 'completed' ? duration : '-' }}
              </dd>
            </div>
          </div>
        </UCard>

        <!-- Results Section -->
        <UCard v-if="experiment.status === 'completed'">
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              Results
            </h2>
          </template>

          <div class="space-y-4">
            <div class="bg-gray-50 rounded-lg p-4">
              <h3 class="text-lg font-medium text-gray-900 mb-2">
                Performance Metrics
              </h3>
            </div>

            <div class="text-sm text-gray-500">
              Results will appear here once the experiment completes.
            </div>
          </div>
        </UCard>

        <!-- Configuration -->
        <UCard>
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              Configuration
            </h2>
          </template>

          <div class="space-y-4">
            <div>
              <h3 class="text-sm font-medium text-gray-900 mb-2">
                Experiment Name
              </h3>
              <p class="text-sm text-gray-600">
                {{ experiment.name }}
              </p>
            </div>
            <div>
              <h3 class="text-sm font-medium text-gray-900 mb-2">
                Agent Teams
              </h3>
              <p class="text-sm text-gray-600">
                Configuration details will be displayed here
              </p>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Error State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-lucide:alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          Experiment Not Found
        </h3>
        <p class="text-gray-500 mb-4">
          The experiment you're looking for doesn't exist.
        </p>
        <UButton to="/" variant="solid" color="primary">
          Return to Dashboard
        </UButton>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteDialog" title="Delete Experiment">
      <template #body>
        <p class="text-gray-600">
          Are you sure you want to delete "{{ experiment?.name }}"? This action cannot be undone.
        </p>
      </template>

      <template #footer>
        <div class="flex gap-3 justify-end">
          <UButton
            variant="outline"
            color="neutral"
            @click="showDeleteDialog = false"
          >
            Cancel
          </UButton>
          <UButton
            variant="solid"
            color="error"
            :loading="isDeleting"
            @click="handleDeleteExperiment"
          >
            Delete
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
