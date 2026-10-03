<script setup lang="ts">
interface Props {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

withDefaults(defineProps<Props>(), {
  message: 'Loading…',
  size: 'md',
})

const sizeClasses = {
  sm: 'size-4',
  md: 'size-5',
  lg: 'size-6',
}
</script>

<template>
  <div class="flex justify-center items-center gap-2 py-16" role="status">
    <UIcon
      name="i-ph-circle-notch-bold"
      class="animate-spin text-muted"
      :class="sizeClasses[size]"
      aria-hidden="true"
    />
    <p class="text-sm text-muted">
      {{ message }}
    </p>
  </div>
</template>
