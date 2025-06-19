<script setup lang="ts">
import type { AgentTeam, CreateAgentForm } from '~/types'

interface Props {
  open?: boolean
  availableTeams?: readonly AgentTeam[]
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateAgentForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  availableTeams: () => [],
})
const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})

// Form state
const formData = ref<CreateAgentForm>({
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

// Initialize form when component mounts
onMounted(() => {
  resetForm()
})

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
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">
            Create New Agent
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
                <UInput
                  v-model="formData.description"
                  class="w-full"

                  placeholder="Brief description of the agent's purpose"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="System Prompt">
                <UInput
                  v-model="formData.system_prompt"
                  class="w-full"
                  placeholder="Enter system prompt"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="User Prompt">
                <UInput
                  v-model="formData.user_prompt"
                  class="w-full"
                  placeholder="Enter user prompt"
                  required
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Variables (JSON)">
                <UInput
                  v-model="formData.variables"
                  class="w-full"
                  placeholder="Enter variables as JSON (e.g. {&quot;key&quot;: &quot;value&quot;})"
                  required
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
              Create Agent
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
