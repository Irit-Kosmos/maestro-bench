<script setup lang="ts">
interface Props {
  title: string
  value: string | number
  icon: string
  iconColor?: string
  loading?: boolean
  href?: string
}

withDefaults(defineProps<Props>(), {
  iconColor: 'text-neutral-400',
  loading: false,
})
</script>

<template>
  <NuxtLink
    :to="href"
    class="group flex flex-col gap-3 px-5 py-4 border border-neutral-200 rounded-lg bg-white hover:border-neutral-300 hover:bg-neutral-50/50 transition-all duration-150"
    :class="{ 'pointer-events-none': !href }"
  >
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-neutral-400 uppercase tracking-wider">{{ title }}</span>
      <UIcon :name="icon" class="size-4" :class="iconColor" />
    </div>
    <div class="text-3xl font-semibold text-neutral-900 tabular-nums leading-none">
      <span v-if="loading" class="inline-block w-12 h-7 bg-neutral-100 rounded animate-pulse" />
      <span v-else>{{ value }}</span>
    </div>
  </NuxtLink>
</template>
