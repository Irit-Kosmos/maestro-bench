<script setup lang="ts">
import type { CreateDatasetForm } from '~/types'

interface Props {
  open?: boolean
  /** The upload is under way: the dialog stays open, and keeps the form if it fails */
  loading?: boolean
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateDatasetForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  loading: false,
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

// Computed
const formValid = computed(() => {
  return formData.value.name.trim() && formData.value.file
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

// The page closes the dialog once the upload went through
function handleSubmit() {
  const { file } = formData.value
  if (!formValid.value || !file || props.loading)
    return

  emit('submit', {
    name: formData.value.name.trim(),
    description: formData.value.description.trim(),
    file,
  })
}
</script>

<template>
  <UModal
    v-model:open="show"
    title="New dataset"
    description="Upload a CSV or JSON file to create a dataset."
    :dismissible="!loading"
    @after:leave="resetForm"
  >
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-base font-semibold text-highlighted">
            New dataset
          </h2>
        </template>

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Basic Information -->
          <div class="grid grid-cols-1 gap-4">
            <div>
              <UFormField label="Name" required>
                <UInput
                  v-model="formData.name"
                  class="w-full"
                  placeholder="e.g. Customer questions"
                  autofocus
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Description">
                <UTextarea
                  v-model="formData.description"
                  class="w-full"
                  placeholder="What the rows are, where they come from"
                  :rows="2"
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="File" required>
                <UFileUpload
                  v-model="formData.file"
                  accept=".csv,.json"
                  label="Drop a file here or browse"
                  description="CSV or JSON. Each row is one input; a CSV’s first line holds the column names."
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
              :disabled="loading"
              @click="handleCancel"
            >
              Cancel
            </UButton>
            <UButton
              type="submit"
              variant="solid"
              color="primary"
              :disabled="!formValid"
              :loading="loading"
            >
              Create dataset
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
