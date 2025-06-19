<script setup lang="ts">
import type { Experiment } from '~/types'

// Composables
const { experiments, pending, refresh } = useExperiments()
const toast = useToast()

// Page meta
useSeoMeta({
  title: 'Experiments',
  description: 'Manage and monitor your AI agent experiments. Create, view, and analyze experiment results.',
})

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

async function handleDeleteExperiment(_id: number) {
  // TODO: Add confirmation dialog
  toast.add({
    title: 'Coming Soon',
    description: 'Delete confirmation dialog coming soon!',
    color: 'info',
    icon: 'i-lucide:info',
  })
}

async function handleCreateExperiment() {
  await navigateTo('/experiments/new')
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Page Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            Experiments
          </h1>
          <p class="text-gray-500 mt-1">
            Manage and monitor your experiments
          </p>
        </div>
        <UButton
          variant="solid"
          color="primary"
          icon="i-lucide:plus"
          size="lg"
          @click="handleCreateExperiment"
        >
          Create Experiment
        </UButton>
      </div>

      <!-- All Experiments Table -->
      <div v-if="experiments && experiments.length > 0">
        <ExperimentsTable
          :experiments="(experiments || []) as Experiment[]"
          :loading="pending"
          @refresh="refresh"
          @view-experiment="handleViewExperiment"
          @delete-experiment="handleDeleteExperiment"
        />
      </div>

      <!-- Empty State -->
      <div v-else-if="!pending" class="text-center py-12">
        <UIcon name="i-lucide:flask-conical" class="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          No experiments yet
        </h3>
        <p class="text-gray-500 mb-6">
          Get started by creating your first experiment to test your agent teams.
        </p>
        <UButton
          variant="solid"
          color="primary"
          icon="i-lucide:plus"
          size="lg"
          @click="handleCreateExperiment"
        >
          Create Your First Experiment
        </UButton>
      </div>

      <!-- Loading State -->
      <div v-else class="flex justify-center items-center py-12">
        <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
      </div>
    </div>
  </div>
</template>
