<script setup lang="ts">
interface Props {
  open: boolean
  title: string
  mode: 'create' | 'edit' | 'view'
  loading?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  size: 'md',
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  'submit': []
  'cancel': []
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
  return `${prefix} ${props.title}`
})

const submitLabel = computed(() => {
  return props.mode === 'create' ? 'Create' : props.mode === 'edit' ? 'Update' : 'Close'
})

function handleSubmit() {
  emit('submit')
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
}

function getSizeClass() {
  return sizeClasses[props.size]
}
</script>

<template>
  <UModal v-model="isOpen">
    <UCard :class="getSizeClass()">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-neutral-900">
            {{ modalTitle }}
          </h3>
          <UButton
            variant="ghost"
            color="neutral"
            icon="i-lucide-x"
            size="sm"
            @click="handleCancel"
          />
        </div>
      </template>

      <!-- Modal Content -->
      <div class="space-y-4">
        <slot />
      </div>

      <template #footer>
        <slot name="footer">
          <div class="flex justify-end gap-3">
            <UButton
              v-if="mode !== 'view'"
              variant="outline"
              color="neutral"
              @click="handleCancel"
            >
              Cancel
            </UButton>
            <UButton
              variant="solid"
              :color="mode === 'view' ? 'neutral' : 'primary'"
              :loading="loading"
              @click="handleSubmit"
            >
              {{ submitLabel }}
            </UButton>
          </div>
        </slot>
      </template>
    </UCard>
  </UModal>
</template>
