<script setup lang="ts">
interface Props {
  version: string
  isDefault?: boolean
  isActive?: boolean
  createdAt?: string
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  isDefault: false,
  isActive: true,
  size: 'md',
})

const headerClasses = computed(() => {
  const sizeClass = props.size === 'sm' ? 'text-sm' : props.size === 'lg' ? 'text-xl' : 'text-lg'
  return `${sizeClass} font-medium text-neutral-900`
})
</script>

<template>
  <div class="flex items-center justify-between w-full">
    <div class="flex items-center space-x-4">
      <h3 :class="headerClasses">
        {{ version }}
      </h3>
      <div class="flex items-center space-x-2">
        <UBadge
          v-if="isDefault"
          label="Default"
          color="success"
          size="sm"
        />
        <UBadge
          v-if="isActive"
          label="Active"
          color="primary"
          variant="subtle"
          size="sm"
        />
        <UBadge
          v-else
          label="Inactive"
          color="error"
          variant="subtle"
          size="sm"
        />
      </div>
    </div>
    <div v-if="createdAt" class="flex items-center space-x-4">
      <span class="text-sm text-neutral-500">
        {{ parseApiDate(createdAt).toLocaleDateString() }}
      </span>
    </div>
  </div>
</template>
