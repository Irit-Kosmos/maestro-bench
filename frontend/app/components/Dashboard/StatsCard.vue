<script setup lang="ts">
interface Props {
  title: string
  value: string | number
  icon: string
  /** Secondary line under the value, e.g. a breakdown */
  detail?: string
  loading?: boolean
  href?: string
}

withDefaults(defineProps<Props>(), {
  detail: undefined,
  loading: false,
  href: undefined,
})
</script>

<template>
  <!-- Hover is instant on purpose: it fires too often to be animated -->
  <NuxtLink
    :to="href"
    class="group flex flex-col gap-2 px-4 py-3.5 rounded-lg border border-default bg-default outline-none hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-primary"
    :class="{ 'pointer-events-none': !href }"
  >
    <div class="flex items-center gap-1.5 text-muted">
      <UIcon :name="icon" class="size-3.5" aria-hidden="true" />
      <span class="text-xs font-medium">{{ title }}</span>
    </div>
    <div class="text-2xl font-semibold text-highlighted tabular-nums leading-none">
      <USkeleton v-if="loading" class="h-6 w-10" />
      <span v-else>{{ value }}</span>
    </div>
    <p v-if="detail && !loading" class="text-xs text-muted tabular-nums truncate">
      {{ detail }}
    </p>
  </NuxtLink>
</template>
