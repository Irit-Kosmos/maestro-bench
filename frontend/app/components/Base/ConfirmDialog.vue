<script setup lang="ts">
interface Props {
  open: boolean
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'error' | 'warning' | 'info'
  loading?: boolean
  /** Why the action failed; shown in the dialog, which stays open so the person can try again */
  error?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  variant: 'warning',
  loading: false,
  error: null,
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

const confirmColor = computed(() => ({ error: 'error', warning: 'warning', info: 'primary' } as const)[props.variant])

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <UModal
    v-model:open="isOpen"
    :title="title"
    :description="message"
    :dismissible="!loading"
    @after:leave="emit('afterLeave')"
  >
    <template v-if="error" #body>
      <UAlert color="error" variant="subtle" icon="i-ph-warning-circle-bold" :description="error" />
    </template>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton variant="outline" color="neutral" :disabled="loading" @click="handleCancel">
          {{ cancelLabel }}
        </UButton>
        <UButton variant="solid" :color="confirmColor" :loading="loading" @click="handleConfirm">
          {{ confirmLabel }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>
