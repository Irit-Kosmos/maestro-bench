<script setup lang="ts">
interface Props {
  loading?: boolean
  error?: string | null
  /** Fills the panel instead of growing with its content, so the page itself never scrolls */
  fill?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  fill: false,
})

defineSlots<{
  'default'?: any
  'before-content'?: any
  'after-content'?: any
}>()
</script>

<template>
  <div :class="fill && 'flex flex-col flex-1 min-h-0'">
    <!-- Page actions live in the top bar, next to the breadcrumb, like the rest of the shell -->
    <AppPageActions v-if="$slots['before-content']">
      <slot name="before-content" />
    </AppPageActions>

    <!-- Loading State -->
    <BaseLoadingState v-if="loading" />

    <!-- Error State -->
    <BaseErrorState v-else-if="error" :message="error" />

    <!-- Main Content -->
    <div v-else :class="fill && 'flex flex-col flex-1 min-h-0'">
      <slot />
    </div>

    <!-- After Content Slot -->
    <div v-if="$slots['after-content']">
      <slot name="after-content" />
    </div>
  </div>
</template>
