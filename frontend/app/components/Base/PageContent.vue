<script setup lang="ts">
interface Props {
  title: string
  subtitle?: string
  loading?: boolean
  error?: string | null
}

withDefaults(defineProps<Props>(), {
  subtitle: undefined,
  loading: false,
  error: null,
})

defineSlots<{
  'default'?: any
  'actions'?: any
  'before-content'?: any
  'after-content'?: any
}>()
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Page Header -->
    <div class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">
          {{ title }}
        </h1>
        <p v-if="subtitle" class="text-neutral-500 mt-1">
          {{ subtitle }}
        </p>
      </div>
      <div v-if="$slots.actions" class="flex gap-3">
        <slot name="actions" />
      </div>
    </div>

    <!-- Before Content Slot -->
    <div v-if="$slots['before-content']">
      <slot name="before-content" />
    </div>

    <!-- Loading State -->
    <BaseLoadingState v-if="loading" />

    <!-- Error State -->
    <BaseErrorState v-else-if="error" :message="error" />

    <!-- Main Content -->
    <div v-else>
      <slot />
    </div>

    <!-- After Content Slot -->
    <div v-if="$slots['after-content']">
      <slot name="after-content" />
    </div>
  </div>
</template>
