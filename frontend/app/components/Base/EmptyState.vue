<script setup lang="ts">
interface Props {
  title?: string
  message?: string
  /** Alias of `message` */
  description?: string
  icon?: string
  /** No button unless a label is given */
  actionLabel?: string
  actionIcon?: string
  actionTo?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'No items found',
  message: undefined,
  description: undefined,
  icon: 'i-lucide-folder-open',
  actionLabel: undefined,
  actionIcon: 'i-lucide-plus',
  actionTo: undefined,
})

const emit = defineEmits<{
  action: []
}>()

defineSlots<{
  default?: any
}>()

const text = computed(() => props.message ?? props.description)

function onAction() {
  if (!props.actionTo)
    emit('action')
}
</script>

<template>
  <div class="flex flex-col items-center text-center py-16 px-4">
    <div class="flex items-center justify-center size-10 rounded-lg bg-elevated ring ring-default mb-4">
      <UIcon :name="icon" class="size-5 text-muted" aria-hidden="true" />
    </div>
    <h3 class="text-sm font-semibold text-highlighted text-balance">
      {{ title }}
    </h3>
    <p v-if="text" class="mt-1 max-w-sm text-sm text-muted text-pretty">
      {{ text }}
    </p>
    <div v-if="$slots.default || actionLabel" class="mt-5 flex items-center gap-2">
      <slot>
        <UButton
          :to="actionTo"
          color="neutral"
          variant="soft"
          :icon="actionIcon"
          size="sm"
          @click="onAction"
        >
          {{ actionLabel }}
        </UButton>
      </slot>
    </div>
  </div>
</template>
