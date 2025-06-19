<script setup lang="ts">
import type { Agent, AgentTeam } from '~/types'

interface Props {
  open?: boolean
  agent?: Agent | null
  availableTeams?: readonly AgentTeam[]
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: { id: number, name: string, description: string, system_prompt: string, user_prompt: string, variables: string, team_id: number }]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  agent: null,
  availableTeams: () => [],
})
const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})

// Form state
const formData = ref({
  name: '',
  description: '',
  system_prompt: '',
  user_prompt: '',
  variables: '[]',
  team_id: 0,
})

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  return formData.value.name.trim()
    && formData.value.description.trim()
    && formData.value.team_id > 0
})

// Methods
function populateForm() {
  if (props.agent) {
    formData.value = {
      name: props.agent.name,
      description: props.agent.description || '',
      system_prompt: props.agent.system_prompt || '',
      user_prompt: props.agent.user_prompt || '',
      variables: props.agent.variables || '[]',
      team_id: props.agent.team_id,
    }
  }
}

function resetForm() {
  formData.value = {
    name: '',
    description: '',
    system_prompt: '',
    user_prompt: '',
    variables: '[]',
    team_id: props.availableTeams?.[0]?.id || 0,
  }
}

function handleCancel() {
  resetForm()
  show.value = false
}

async function handleSubmit() {
  if (!formValid.value || !props.agent)
    return

  isSubmitting.value = true
  try {
    emit('submit', {
      id: props.agent.id,
      ...formData.value,
    })
    show.value = false
  }
  finally {
    isSubmitting.value = false
  }
}

// Watch for agent changes to populate form
watch(() => props.agent, () => {
  if (props.agent && props.open) {
    populateForm()
  }
}, { immediate: true })

// Watch for modal open/close
watch(() => props.open, (newValue) => {
  if (newValue && props.agent) {
    populateForm()
  }
  else if (!newValue) {
    resetForm()
  }
})
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isSubmitting">
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">
            Edit Agent
          </h2>
        </template>

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Basic Information -->
          <div class="grid grid-cols-1 gap-4">
            <div>
              <UFormField label="Agent Name">
                <UInput
                  v-model="formData.name"
                  class="w-full"
                  placeholder="Enter agent name"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Description">
                <UTextarea
                  v-model="formData.description"
                  class="w-full"
                  placeholder="Brief description of the agent's purpose"
                  :rows="3"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="System Prompt">
                <UTextarea
                  v-model="formData.system_prompt"
                  class="w-full"
                  placeholder="Enter system prompt"
                  :rows="4"
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="User Prompt">
                <UTextarea
                  v-model="formData.user_prompt"
                  class="w-full"
                  placeholder="Enter user prompt"
                  :rows="4"
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Variables (JSON)">
                <UTextarea
                  v-model="formData.variables"
                  class="w-full"
                  placeholder="Enter variables as JSON (e.g. [&quot;key1&quot;, &quot;key2&quot;])"
                  :rows="2"
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Agent Team">
                <USelect
                  v-model="formData.team_id"
                  :items="availableTeams?.map(team => ({ label: team.name, value: team.id })) || []"
                  class="w-full"
                  placeholder="Select a team"
                  required
                />
              </UFormField>
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
              Update Agent
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
