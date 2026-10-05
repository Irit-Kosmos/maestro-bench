<script setup lang="ts">
import type { FetchErrorKind } from '~/utils/fetchError'

interface Props {
  loading?: boolean
  /** Shown instead of the content (true: the default wording); leave it empty while earlier data is still on screen */
  error?: string | boolean | null
  errorKind?: FetchErrorKind
  /** Where the error state leads back to */
  backTo?: string
  backLabel?: string
  /** Fills the panel instead of growing with its content, so the page itself never scrolls */
  fill?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  errorKind: 'error',
  backTo: '/',
  backLabel: 'Back to dashboard',
  fill: false,
})

const emit = defineEmits<{
  retry: []
}>()

defineSlots<{
  'default'?: any
  'before-content'?: any
  'after-content'?: any
}>()

// Without a handler the error state reloads the whole app
const onRetry = getCurrentInstance()?.vnode.props?.onRetry ? () => emit('retry') : undefined
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
    <BaseErrorState
      v-else-if="error"
      :kind="errorKind"
      :message="typeof error === 'string' ? error : undefined"
      :action-to="backTo"
      :action-label="backLabel"
      v-bind="onRetry ? { onRetry } : {}"
    />

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
