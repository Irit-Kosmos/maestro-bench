<script setup lang="ts">
import type { Agent, CreateAgentTeamForm } from '~/types'

interface Props {
  open?: boolean
  availableAgents?: readonly Agent[]
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateAgentTeamForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  availableAgents: () => [],
})

const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})

// Form state
const formData = ref<CreateAgentTeamForm>({
  name: '',
  description: '',
  agent_ids: [],
})

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  return formData.value.name.trim()
    && formData.value.description.trim()
})

// Methods
function resetForm() {
  formData.value = {
    name: '',
    description: '',
    agent_ids: [],
  }
}

function handleCancel() {
  resetForm()
  show.value = false
}

async function handleSubmit() {
  if (!formValid.value)
    return

  isSubmitting.value = true
  try {
    emit('submit', { ...formData.value })
    resetForm()
    show.value = false
  }
  finally {
    isSubmitting.value = false
  }
}

function toggleAgent(agentId: number) {
  if (!formData.value.agent_ids) {
    formData.value.agent_ids = []
  }
  const index = formData.value.agent_ids.indexOf(agentId)
  if (index > -1) {
    formData.value.agent_ids.splice(index, 1)
  }
  else {
    formData.value.agent_ids.push(agentId)
  }
}

// Watch for modal close to reset form
watch(() => props.open, (newValue) => {
  if (!newValue) {
    resetForm()
  }
})
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isSubmitting">
    <template #content>
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">
            Create New Agent Team
          </h2>
        </template>

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Basic Information -->
          <div class="space-y-4">
            <div>
              <label for="team-name" class="block text-sm font-medium text-gray-700 mb-1">
                Team Name
              </label>
              <input
                id="team-name"
                v-model="formData.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter team name (e.g., 'Math Assessment Team')"
              >
            </div>

            <div>
              <label for="team-description" class="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                id="team-description"
                v-model="formData.description"
                rows="3"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Describe what this team does..."
              />
            </div>
          </div>

          <!-- Agent Selection -->
          <div class="space-y-4">
            <h3 class="text-md font-medium text-gray-900">
              Select Agents (Optional)
            </h3>
            <p class="text-sm text-gray-600">
              You can add agents to this team now or later. Teams can start empty.
            </p>

            <div v-if="availableAgents.length === 0" class="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
              <UIcon name="i-lucide:users" class="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p class="text-sm text-gray-500">
                No agents available. Create agents first.
              </p>
            </div>

            <div v-else class="space-y-2 max-h-60 overflow-y-auto">
              <div
                v-for="agent in availableAgents"
                :key="agent.id"
                class="flex items-start space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                @click="toggleAgent(agent.id)"
              >
                <input
                  :id="`agent-${agent.id}`"
                  v-model="formData.agent_ids"
                  type="checkbox"
                  :value="agent.id"
                  class="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded pointer-events-none"
                >
                <div class="flex-1 pointer-events-none">
                  <h4 class="text-sm font-medium text-gray-900">
                    {{ agent.name }}
                  </h4>
                  <p class="text-sm text-gray-600">
                    {{ agent.description }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end pt-4 border-t border-gray-200">
            <UButton
              type="button"
              variant="outline"
              color="neutral"
              :disabled="isSubmitting"
              @click="handleCancel"
            >
              Cancel
            </UButton>
            <UButton
              type="submit"
              variant="solid"
              color="primary"
              :disabled="!formValid || isSubmitting"
              :loading="isSubmitting"
            >
              Create Team
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
