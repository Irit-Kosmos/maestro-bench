<script setup lang="ts">
interface Props {
  open: boolean
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'error' | 'warning' | 'info'
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm Action',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  variant: 'warning',
  loading: false,
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  'confirm': []
  'cancel': []
  'afterLeave': []
}>()

const isOpen = computed({
  get: () => props.open,
  set: value => emit('update:open', value),
})

const variantConfig = computed(() => {
  const configs = {
    error: {
      color: 'error' as const,
      icon: 'i-lucide-alert-triangle',
      iconColor: 'text-error',
    },
    warning: {
      color: 'warning' as const,
      icon: 'i-lucide-alert-circle',
      iconColor: 'text-warning',
    },
    info: {
      color: 'primary' as const,
      icon: 'i-lucide-info',
      iconColor: 'text-info',
    },
  }
  return configs[props.variant]
})

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <UModal v-model:open="isOpen" @after:leave="emit('afterLeave')">
    <template #content>
      <UCard>
        <template #header>
          <div class="flex items-center gap-3">
            <UIcon :name="variantConfig.icon" :class="variantConfig.iconColor" class="h-6 w-6" />
            <h3 class="text-lg font-semibold text-highlighted">
              {{ title }}
            </h3>
          </div>
        </template>

        <div class="py-4">
          <p class="text-toned">
            {{ message }}
          </p>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton
              variant="outline"
              color="neutral"
              @click="handleCancel"
            >
              {{ cancelLabel }}
            </UButton>
            <UButton
              variant="solid"
              :color="variantConfig.color"
              :loading="loading"
              @click="handleConfirm"
            >
              {{ confirmLabel }}
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>
