<script setup lang="ts">
import type { CreateDatasetForm } from '~/types'

interface Props {
  loading?: boolean
}

interface Emits {
  submit: [data: CreateDatasetForm]
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const formData = ref<CreateDatasetForm>({
  name: '',
  description: '',
})

const formValid = computed(() => {
  return formData.value.name.trim() && formData.value.description.trim()
})

function handleSubmit() {
  if (!formValid.value)
    return

  emit('submit', {
    name: formData.value.name.trim(),
    description: formData.value.description.trim(),
  })

  // Reset form
  formData.value.name = ''
  formData.value.description = ''
}
</script>

<template>
  <div class="bg-white rounded-lg shadow">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900">
        Create New Dataset
      </h2>
    </div>
    <div class="p-6">
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="name" class="block text-sm font-medium text-gray-700 mb-1">
              Dataset Name
            </label>
            <input
              id="name"
              v-model="formData.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter dataset name"
            >
          </div>
          <div>
            <label for="description" class="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <input
              id="description"
              v-model="formData.description"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter dataset description"
            >
          </div>
        </div>
        <div class="flex justify-end items-center gap-4">
          <UButton
            type="submit"
            :disabled="loading || !formValid"
            :loading="loading"
            variant="solid"
            color="primary"
            icon="i-lucide:plus"
          >
            Create Dataset
          </UButton>
        </div>
      </form>
    </div>
  </div>
</template>
