<script setup lang="ts">
interface Props {
  modelValue: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  loading?: boolean
}

interface Emits {
  'update:modelValue': [value: boolean]
  'confirm': []
  'cancel': []
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm Action',
  message: 'Are you sure you want to proceed? This action cannot be undone.',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  loading: false,
})

const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  show.value = false
}
</script>

<template>
  <UModal v-model="show">
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold text-gray-900">
          {{ title }}
        </h2>
      </template>

      <div class="space-y-4">
        <p class="text-gray-600">
          {{ message }}
        </p>

        <div class="flex gap-3 justify-end">
          <UButton
            variant="outline"
            color="neutral"
            :disabled="loading"
            @click="handleCancel"
          >
            {{ cancelText }}
          </UButton>
          <UButton
            variant="solid"
            color="error"
            :loading="loading"
            @click="handleConfirm"
          >
            {{ confirmText }}
          </UButton>
        </div>
      </div>
    </UCard>
  </UModal>
</template>
