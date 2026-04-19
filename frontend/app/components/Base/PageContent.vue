<script setup lang="ts">
interface Props {
  loading?: boolean
  error?: string | null
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

defineSlots<{
  'default'?: any
  'before-content'?: any
  'after-content'?: any
}>()
</script>

<template>
  <div class="max-w-[350]">
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
