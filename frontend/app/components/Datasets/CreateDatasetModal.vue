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
const formData = ref({
  name: '',
  description: '',
  file: null as File | null,
})

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  return formData.value.name.trim()
    && formData.value.description.trim()
    && formData.value.file
})

// The file names the dataset until the user types another name
watch(() => formData.value.file, (file, previous) => {
  const stem = (value: File | null) => value?.name.replace(/\.[^.]+$/, '') ?? ''
  if (file && (!formData.value.name.trim() || formData.value.name === stem(previous)))
    formData.value.name = stem(file)
})

// Methods
function resetForm() {
  formData.value = {
    name: '',
    description: '',
    file: null,
  }
}

function handleCancel() {
  show.value = false
}

async function handleSubmit() {
  const { file } = formData.value
  if (!formValid.value || !file)
    return

  isSubmitting.value = true
  try {
    const submitData: CreateDatasetForm = {
      name: formData.value.name.trim(),
      description: formData.value.description.trim(),
      file,
    }

    emit('submit', submitData)
    show.value = false
  }
  finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isSubmitting" @after:leave="resetForm">
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-lg font-semibold text-highlighted">
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
              <UFormField label="File">
                <UFileUpload
                  v-model="formData.file"
                  accept=".csv,.json"
                  label="Drop a file here or browse"
                  description="CSV or JSON, one row per input"
                  icon="i-ph-file-arrow-up-bold"
                  class="w-full min-h-32"
                />
              </UFormField>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end pt-4 border-t border-default">
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
              icon="i-ph:plus-bold"
            >
              Create Dataset
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
