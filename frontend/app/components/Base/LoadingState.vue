<script setup lang="ts">
interface Props {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

withDefaults(defineProps<Props>(), {
  message: 'Loading...',
  size: 'md',
})

const sizeClasses = {
  sm: 'w-6 h-6',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
}
</script>

<template>
  <div class="flex justify-center items-center py-12">
    <div class="text-center">
      <UIcon
        name="i-lucide:loader-2"
        class="animate-spin text-primary-500 mx-auto mb-2"
        :class="sizeClasses[size]"
      />
      <p class="text-neutral-500 text-sm">
        {{ message }}
      </p>
    </div>
  </div>
</template>
