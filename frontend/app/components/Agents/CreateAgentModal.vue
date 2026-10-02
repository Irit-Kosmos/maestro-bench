<script setup lang="ts">
import type { AgentTeam, CreateAgentForm, Model, PromptVersion } from '~/types'

interface Props {
  open?: boolean
  availableTeams?: readonly AgentTeam[]
  availablePromptVersions?: readonly PromptVersion[]
  availableModels?: readonly Model[]
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateAgentForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  availableTeams: () => [],
  availablePromptVersions: () => [],
  availableModels: () => [],
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
  default_prompt_version_id: null,
  default_model_id: null,
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
    default_prompt_version_id: null,
    default_model_id: null,
    team_id: props.availableTeams?.[0]?.id || 0,
  }
}

function handleCancel() {
  show.value = false
}

async function handleSubmit() {
  if (!formValid.value)
    return

  isSubmitting.value = true
  try {
    emit('submit', { ...formData.value })
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
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isSubmitting" @after:leave="resetForm">
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-lg font-semibold text-highlighted">
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

            <div>
              <UFormField label="Default Prompt Version (Optional)">
                <PromptsSelect
                  v-model="formData.default_prompt_version_id"
                  :prompt-versions="availablePromptVersions"
                  clearable
                  class="w-full"
                  placeholder="No default prompt"
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Default Model (Optional)">
                <ModelsSelect
                  v-model="formData.default_model_id"
                  :models="availableModels"
                  clearable
                  class="w-full"
                  placeholder="Select a default model"
                />
              </UFormField>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end pt-4 border-t border-default">
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
