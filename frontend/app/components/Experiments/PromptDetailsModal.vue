<script setup lang="ts">
interface Props {
  isOpen: boolean
  promptVersionDetails: any
}

interface Emits {
  'update:isOpen': [value: boolean]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOpen = computed({
  get: () => props.isOpen,
  set: (value: boolean) => emit('update:isOpen', value),
})
</script>

<template>
  <UModal
    v-model:open="isOpen" :ui="{ content: 'lg:min-w-1/2' }"
  >
    <template #content>
      <UCard class="overflow-auto max-h-[80vh]">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold leading-6 text-neutral-900 dark:text-white">
              Prompt Details: {{ promptVersionDetails?.prompt?.name }} v{{ promptVersionDetails?.version }}
            </h3>
            <UButton color="neutral" variant="ghost" icon="i-lucide-x" class="-my-1" @click="isOpen = false" />
          </div>
        </template>

        <div v-if="promptVersionDetails" class="space-y-6">
          <!-- Basic Info -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                Prompt Name
              </h4>
              <p class="text-sm text-neutral-600 dark:text-neutral-300">
                {{ promptVersionDetails.prompt?.name || 'Unknown' }}
              </p>
            </div>
            <div>
              <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                Version
              </h4>
              <div class="flex items-center gap-2">
                <UBadge size="sm" variant="subtle">
                  v{{ promptVersionDetails.version }}
                </UBadge>
                <UBadge v-if="promptVersionDetails.is_default" size="sm" color="success">
                  Default
                </UBadge>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div v-if="promptVersionDetails.prompt?.description">
            <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
              Description
            </h4>
            <p class="text-sm text-neutral-600 dark:text-neutral-300">
              {{ promptVersionDetails.prompt.description }}
            </p>
          </div>

          <!-- System Prompt -->
          <div v-if="promptVersionDetails.system_prompt">
            <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
              System Prompt
            </h4>
            <div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4">
              <pre class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{{ promptVersionDetails.system_prompt }}</pre>
            </div>
          </div>

          <!-- User Prompt -->
          <div v-if="promptVersionDetails.user_prompt">
            <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
              User Prompt
            </h4>
            <div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4">
              <pre class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{{ promptVersionDetails.user_prompt }}</pre>
            </div>
          </div>

          <!-- Variables -->
          <div v-if="promptVersionDetails.variables">
            <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
              Variables
            </h4>
            <div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4">
              <pre class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{{ promptVersionDetails.variables }}</pre>
            </div>
          </div>

          <!-- Notes -->
          <div v-if="promptVersionDetails.notes">
            <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
              Notes
            </h4>
            <p class="text-sm text-neutral-600 dark:text-neutral-300">
              {{ promptVersionDetails.notes }}
            </p>
          </div>

          <!-- Metadata -->
          <div class="border-t pt-4">
            <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
              Metadata
            </h4>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-neutral-500 dark:text-neutral-400">Created:</span>
                <span class="ml-2 text-neutral-700 dark:text-neutral-300">{{ new Date(promptVersionDetails.created_at).toLocaleDateString() }}</span>
              </div>
              <div>
                <span class="text-neutral-500 dark:text-neutral-400">Category:</span>
                <span class="ml-2 text-neutral-700 dark:text-neutral-300">{{ promptVersionDetails.prompt?.category || 'Uncategorized' }}</span>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end">
            <UButton color="neutral" variant="solid" @click="isOpen = false">
              Close
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>
