<script setup lang="ts">
import type { Agent } from '~/types'

interface Props {
  open?: boolean
  agent?: Agent | null
}

interface Emits {
  'update:open': [value: boolean]
  'confirm': [agentId: number]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  agent: null,
})
const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})

const isDeleting = ref(false)

// Methods
function handleCancel() {
  show.value = false
}

async function handleConfirm() {
  if (!props.agent)
    return

  isDeleting.value = true
  try {
    emit('confirm', props.agent.id)
    show.value = false
  }
  finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isDeleting">
    <template #content>
      <UCard>
        <template #header>
          <div class="flex items-center space-x-3">
            <div class="flex-shrink-0 flex items-center">
              <UIcon name="i-lucide:alert-triangle" class="w-6 h-6 text-error" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-neutral-900">
                Delete Agent
              </h2>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <p class="text-sm text-neutral-600">
            Are you sure you want to delete the agent
            <span class="font-semibold text-neutral-900">"{{ agent?.name }}"</span>?
          </p>

          <div class="bg-error-50 border border-error-200 rounded-md p-3">
            <div class="flex">
              <UIcon name="i-lucide:info" class="w-5 h-5 text-error-400 mt-0.5 mr-2" />
              <div class="text-sm text-error-700">
                <p class="font-medium">
                  This action cannot be undone.
                </p>
                <p class="mt-1">
                  The agent will be permanently removed from the system and any associated configurations will be lost.
                </p>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex gap-3 justify-end">
            <UButton
              type="button"
              variant="outline"
              color="neutral"
              :disabled="isDeleting"
              @click="handleCancel"
            >
              Cancel
            </UButton>
            <UButton
              type="button"
              variant="solid"
              color="error"
              :disabled="isDeleting"
              :loading="isDeleting"
              @click="handleConfirm"
            >
              Delete Agent
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>
