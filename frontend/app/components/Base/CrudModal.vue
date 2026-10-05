<script setup lang="ts">
interface Props {
  open: boolean
  title: string
  mode: 'create' | 'edit' | 'view'
  loading?: boolean
  /** Holds the submit button back while the form is not valid */
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  disabled: false,
  size: 'md',
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  'submit': []
  'cancel': []
  'afterLeave': []
}>()

defineSlots<{
  default?: any
  footer?: any
}>()

const isOpen = computed({
  get: () => props.open,
  set: value => emit('update:open', value),
})

const modalTitle = computed(() => {
  const prefix = props.mode === 'create' ? 'Create' : props.mode === 'edit' ? 'Edit' : 'View'
  return `${prefix} ${props.title.toLowerCase()}`
})

const submitLabel = computed(() => {
  return props.mode === 'create' ? 'Create' : props.mode === 'edit' ? 'Save' : 'Close'
})

function handleSubmit() {
  emit('submit')
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <UModal v-model:open="isOpen" @after:leave="emit('afterLeave')">
    <template #content>
      <!-- A real form: Enter submits, and the button waits for a valid one -->
      <form @submit.prevent="handleSubmit">
        <UCard class="w-full">
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="text-base font-semibold text-highlighted">
                {{ modalTitle }}
              </h3>
              <UButton
                type="button"
                variant="ghost"
                color="neutral"
                icon="i-ph-x-bold"
                size="sm"
                aria-label="Close"
                @click="handleCancel"
              />
            </div>
          </template>

          <div class="space-y-4">
            <slot />
          </div>

          <template #footer>
            <slot name="footer">
              <div class="flex justify-end gap-2">
                <UButton
                  v-if="mode !== 'view'"
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
                  :color="mode === 'view' ? 'neutral' : 'primary'"
                  :loading="loading"
                  :disabled="disabled"
                >
                  {{ submitLabel }}
                </UButton>
              </div>
            </slot>
          </template>
        </UCard>
      </form>
    </template>
  </UModal>
</template>
