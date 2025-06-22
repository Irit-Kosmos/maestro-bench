<script setup lang="ts">
interface Props {
  title?: string
  message?: string
  icon?: string
  actionLabel?: string
  actionTo?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'No items found',
  message: 'Get started by creating your first item.',
  icon: 'i-lucide:folder-open',
  actionLabel: 'Create Item',
  actionTo: undefined,
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
    <UIcon :name="icon" class="w-16 h-16 text-neutral-400 mx-auto mb-4" />
    <h3 class="text-lg font-medium text-neutral-900 mb-2">
      {{ title }}
    </h3>
    <p class="text-neutral-500 mb-6">
      {{ message }}
    </p>
    <UButton
      v-if="actionLabel"
      :to="actionTo"
      variant="solid"
      color="primary"
      icon="i-lucide:plus"
      size="lg"
      @click="handleAction"
    >
      {{ actionLabel }}
    </UButton>
  </div>
</template>
