<script setup lang="ts">
interface Props {
  message?: string
  title?: string
  icon?: string
  actionLabel?: string
  actionTo?: string
}

const props = withDefaults(defineProps<Props>(), {
  message: 'Something went wrong. Please try again.',
  title: 'Error',
  icon: 'i-lucide:alert-circle',
  actionLabel: 'Go Back',
  actionTo: '/',
})

const emit = defineEmits<{
  action: []
}>()

function handleAction() {
  if (props.actionTo) {
    navigateTo(props.actionTo)
  }
  else {
    emit('action')
  }
}
</script>

<template>
  <div class="text-center py-12">
    <UIcon :name="icon" class="w-12 h-12 text-red-500 mx-auto mb-4" />
    <h3 class="text-lg font-medium text-neutral-900 mb-2">
      {{ title }}
    </h3>
    <p class="text-neutral-500 mb-4">
      {{ message }}
    </p>
    <UButton
      :to="actionTo"
      variant="solid"
      color="primary"
      @click="handleAction"
    >
      {{ actionLabel }}
    </UButton>
  </div>
</template>
