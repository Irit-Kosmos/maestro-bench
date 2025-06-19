<script setup lang="ts">
import type { CreateDatasetForm } from '~/types'

interface Props {
  open?: boolean
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateDatasetForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
})

const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})

// Form state
const formData = ref<CreateDatasetForm>({
  name: '',
  description: '',
  file_path: '',
})

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  return formData.value.name.trim()
    && formData.value.description.trim()
})

// Methods
function resetForm() {
  formData.value = {
    name: '',
    description: '',
    file_path: '',
  }
}

function handleCancel() {
  resetForm()
  show.value = false
}

async function handleSubmit() {
  if (!formValid.value)
    return

  isSubmitting.value = true
  try {
    // Clean up the form data before emitting
    const submitData: CreateDatasetForm = {
      name: formData.value.name.trim(),
      description: formData.value.description.trim(),
    }

    // Only include file_path if it's not empty
    if (formData.value.file_path?.trim()) {
      submitData.file_path = formData.value.file_path.trim()
    }

    emit('submit', submitData)
    resetForm()
    show.value = false
  }
  finally {
    isSubmitting.value = false
  }
}

// Watch for modal close to reset form
watch(() => props.open, (newValue) => {
  if (!newValue) {
    resetForm()
  }
})
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isSubmitting">
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">
            Create New Dataset
          </h2>
        </template>

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Basic Information -->
          <div class="grid grid-cols-1 gap-4">
            <div>
              <UFormField label="Dataset Name">
                <UInput
                  v-model="formData.name"
                  class="w-full"
                  placeholder="Enter dataset name"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Description">
                <UTextarea
                  v-model="formData.description"
                  class="w-full"
                  placeholder="Brief description of the dataset"
                  :rows="3"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="File Path (Optional)">
                <UInput
                  v-model="formData.file_path"
                  class="w-full"
                  placeholder="Enter file path (e.g., /path/to/dataset.csv)"
                />
                <template #help>
                  <span class="text-xs text-gray-500">
                    You can specify a file path or upload a file later
                  </span>
                </template>
              </UFormField>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end pt-4 border-t border-gray-200">
            <UButton
              type="button"
              variant="outline"
              color="neutral"
              :disabled="isSubmitting"
              @click="handleCancel"
            >
              Cancel
            </UButton>
            <UButton
              type="submit"
              variant="solid"
              color="primary"
              :disabled="!formValid || isSubmitting"
              :loading="isSubmitting"
              icon="i-lucide:plus"
            >
              Create Dataset
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
