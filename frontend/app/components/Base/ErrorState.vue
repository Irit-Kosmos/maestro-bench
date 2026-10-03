<script setup lang="ts">
interface Props {
  message?: string
  title?: string
  icon?: string
  actionLabel?: string
  actionTo?: string
}

withDefaults(defineProps<Props>(), {
  message: 'Something went wrong. Check that the backend is running, then try again.',
  title: 'Couldn’t load this page',
  icon: 'i-ph-warning-circle-bold',
  actionLabel: 'Back to dashboard',
  actionTo: '/',
})

function retry() {
  reloadNuxtApp()
}
</script>

<template>
  <div class="flex flex-col items-center text-center py-16 px-4" role="alert">
    <div class="flex items-center justify-center size-10 rounded-lg bg-error/10 mb-4">
      <UIcon :name="icon" class="size-5 text-error" aria-hidden="true" />
    </div>
    <h3 class="text-sm font-semibold text-highlighted">
      {{ title }}
    </h3>
    <p class="mt-1 max-w-sm text-sm text-muted text-pretty">
      {{ message }}
    </p>
    <div class="mt-5 flex items-center gap-2">
      <UButton color="neutral" variant="outline" size="sm" icon="i-ph-arrow-clockwise-bold" @click="retry">
        Try again
      </UButton>
      <UButton :to="actionTo" color="neutral" variant="ghost" size="sm">
        {{ actionLabel }}
      </UButton>
    </div>
  </div>
</template>
