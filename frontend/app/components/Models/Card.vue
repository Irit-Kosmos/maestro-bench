<script setup lang="ts">
import type { Model } from '~/types'

interface Props {
  model: Model
}

interface Emits {
  edit: [model: Model]
  delete: [model: Model]
  toggleStatus: [model: Model]
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<template>
  <UCard>
    <div class="flex justify-between items-start">
      <div class="flex-1">
        <!-- Header with name and status -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <h3 class="text-xl font-semibold text-gray-900">
              {{ model.name }}
            </h3>
            <UBadge
              :color="model.is_active ? 'success' : 'neutral'"
              variant="soft"
              size="sm"
            >
              {{ model.is_active ? 'Active' : 'Inactive' }}
            </UBadge>
          </div>
        </div>

        <!-- Provider Badge -->
        <div class="mb-3">
          <UBadge
            color="neutral"
            variant="outline"
            size="md"
            class="font-medium"
          >
            <UIcon
              name="i-heroicons-building-office"
              class="w-3 h-3 mr-1.5"
            />
            {{ model.provider.charAt(0).toUpperCase() + model.provider.slice(1) }}
          </UBadge>
        </div>

        <!-- Model Details -->
        <div class="space-y-2 text-sm text-gray-600">
          <div v-if="model.description" class="flex items-start gap-2">
            <UIcon name="i-heroicons-document-text" class="w-4 h-4 mt-0.5 text-gray-400" />
            <span class="flex-1">{{ model.description }}</span>
          </div>

          <div v-if="model.max_tokens" class="flex items-center gap-2">
            <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4 text-gray-400" />
            <span class="font-medium">Max Tokens:</span>
            <span class="font-mono text-gray-700">{{ model.max_tokens?.toLocaleString() }}</span>
          </div>

          <div class="flex items-center gap-2">
            <UIcon name="i-heroicons-calendar" class="w-4 h-4 text-gray-400" />
            <span class="font-medium">Created:</span>
            <span>{{ new Date(model.created_at).toLocaleDateString() }}</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-1 ml-4">
        <UButton
          :icon="model.is_active ? 'i-heroicons-pause' : 'i-heroicons-play'"
          :color="model.is_active ? 'warning' : 'success'"
          variant="ghost"
          size="sm"
          class="rounded-full"
          @click="$emit('toggleStatus', model)"
        />

        <UButton
          icon="i-heroicons-pencil"
          color="neutral"
          variant="ghost"
          size="sm"
          class="rounded-full"
          @click="$emit('edit', model)"
        />

        <UButton
          icon="i-heroicons-trash"
          color="error"
          variant="ghost"
          size="sm"
          class="rounded-full"
          @click="$emit('delete', model)"
        />
      </div>
    </div>
  </UCard>
</template>
