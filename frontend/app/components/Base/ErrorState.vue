<script setup lang="ts">
import type { FetchErrorKind } from '~/utils/fetchError'

interface Props {
  /** What went wrong: a failed request, a missing item, or a role that is not enough */
  kind?: FetchErrorKind
  message?: string
  title?: string
  icon?: string
  actionLabel?: string
  actionTo?: string
}

const props = withDefaults(defineProps<Props>(), {
  kind: 'error',
  message: undefined,
  title: undefined,
  icon: undefined,
  actionLabel: 'Back to dashboard',
  actionTo: '/',
})

const emit = defineEmits<{
  retry: []
}>()

const COPY: Record<FetchErrorKind, { title: string, message: string, icon: string }> = {
  'error': {
    title: 'Couldn’t load this',
    message: 'Check your connection and try again.',
    icon: 'i-ph-warning-circle-bold',
  },
  'not-found': {
    title: 'Not found',
    message: 'This page doesn’t exist, or it was deleted.',
    icon: 'i-ph-magnifying-glass-bold',
  },
  'forbidden': {
    title: 'No access',
    message: 'Your role in this workspace doesn’t allow this.',
    icon: 'i-ph-lock-simple-bold',
  },
}

const copy = computed(() => ({
  title: props.title ?? COPY[props.kind].title,
  message: props.message ?? COPY[props.kind].message,
  icon: props.icon ?? COPY[props.kind].icon,
}))

// Trying again only helps when the request itself failed
const canRetry = computed(() => props.kind === 'error')

// A parent that handles `retry` reloads its own data; otherwise reload the app
const hasRetryHandler = !!getCurrentInstance()?.vnode.props?.onRetry

function retry() {
  if (hasRetryHandler)
    emit('retry')
  else
    reloadNuxtApp()
}
</script>

<template>
  <div class="flex flex-col items-center text-center py-16 px-4" role="alert">
    <div class="flex items-center justify-center size-10 rounded-lg bg-error/10 mb-4">
      <UIcon :name="copy.icon" class="size-5 text-error" aria-hidden="true" />
    </div>
    <h3 class="text-sm font-semibold text-highlighted">
      {{ copy.title }}
    </h3>
    <p class="mt-1 max-w-sm text-sm text-muted text-pretty">
      {{ copy.message }}
    </p>
    <div class="mt-5 flex items-center gap-2">
      <UButton v-if="canRetry" color="neutral" variant="outline" size="sm" icon="i-ph-arrow-clockwise-bold" @click="retry">
        Try again
      </UButton>
      <UButton :to="actionTo" color="neutral" variant="ghost" size="sm">
        {{ actionLabel }}
      </UButton>
    </div>
  </div>
</template>
