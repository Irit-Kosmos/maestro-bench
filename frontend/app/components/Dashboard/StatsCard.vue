<script setup lang="ts">
interface Props {
  title: string
  value: string | number
  icon: string
  iconColor?: string
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  iconColor: 'text-blue-600',
  loading: false,
})
</script>

<template>
  <div class="bg-white rounded-lg shadow p-6 flex-1 min-w-[280px]">
    <div class="flex items-center">
      <div class="flex-shrink-0">
        <UIcon :name="icon" class="h-8 w-8" :class="iconColor" />
      </div>
      <div class="ml-5 w-0 flex-1">
        <dl>
          <dt class="text-sm font-medium text-gray-500 truncate">
            {{ title }}
          </dt>
          <dd class="text-2xl font-semibold text-gray-900">
            {{ loading ? '...' : value }}
          </dd>
        </dl>
      </div>
    </div>
  </div>
</template>
