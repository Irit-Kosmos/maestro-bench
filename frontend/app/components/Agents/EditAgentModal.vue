<script setup lang="ts">
import type { Agent, AgentTeam, Model, PromptVersion } from '~/types'

interface Props {
  open?: boolean
  agent?: Agent | null
  availableTeams?: readonly AgentTeam[]
  availablePromptVersions?: readonly PromptVersion[]
  availableModels?: readonly Model[]
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: { id: number, name: string, description: string, default_prompt_version_id: number | null, default_model_id: number | null, team_id: number }]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  agent: null,
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
const formData = ref({
  name: '',
  description: '',
  default_prompt_version_id: null as number | null,
  default_model_id: null as number | null,
  team_id: 0,
})

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  return formData.value.name.trim()
    && formData.value.description.trim()
    && formData.value.team_id > 0
})

const promptVersionOptions = computed(() => {
  if (!props.availablePromptVersions)
    return []
  return props.availablePromptVersions.map((version: any) => ({
    label: `${version.prompt?.name || 'Unknown'} v${version.version}`,
    value: version.id,
  }))
})

const modelOptions = computed(() => {
  if (!props.availableModels)
    return []
  return props.availableModels
    .filter((model: any) => model.is_active)
    .map((model: any) => ({
      label: `${model.name} (${model.provider})`,
      value: model.id,
    }))
})

// Methods
function populateForm() {
  if (props.agent) {
    formData.value = {
      name: props.agent.name,
      description: props.agent.description || '',
      default_prompt_version_id: props.agent.default_prompt_version_id,
      default_model_id: props.agent.default_model_id,
      team_id: props.agent.team_id,
    }
  }
}

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
          <h2 class="text-lg font-semibold text-neutral-900">
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
              <UFormField label="Default Prompt Version">
                <USelect
                  v-model="formData.default_prompt_version_id"
                  :items="[{ label: 'No default prompt', value: null }, ...promptVersionOptions]"
                  class="w-full"
                  placeholder="Select a default prompt version"
                />
              </UFormField>
            </div>

            <div>
              <UFormField label="Default Model">
                <USelect
                  v-model="formData.default_model_id"
                  :items="[{ label: 'No default model', value: null }, ...modelOptions]"
                  class="w-full"
                  placeholder="Select a default model"
                />
              </UFormField>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end pt-4 border-t border-neutral-200">
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
