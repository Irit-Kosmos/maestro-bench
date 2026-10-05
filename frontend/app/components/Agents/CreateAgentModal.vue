<script setup lang="ts">
import type { AgentKind, AgentTeam, CreateAgentForm, Model, PromptVersion } from '~/types'

interface Props {
  open?: boolean
  availableTeams?: readonly AgentTeam[]
  availablePromptVersions?: readonly PromptVersion[]
  availableModels?: readonly Model[]
  /** Kind selected when the modal opens */
  initialKind?: AgentKind
  /** Hides the kind switch: the modal only creates `initialKind` agents */
  lockKind?: boolean
  /** Team selected when the modal opens; the first team otherwise */
  initialTeamId?: number
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
  initialKind: 'llm',
  lockKind: false,
  initialTeamId: undefined,
})
const emit = defineEmits<Emits>()

const show = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})

// Form state
const formData = ref<CreateAgentForm & { tag_ids: number[] }>({
  name: '',
  description: '',
  kind: 'llm',
  default_prompt_version_id: null,
  default_model_id: null,
  team_id: 0,
  tag_ids: [],
})

const aggregator = computed(() => formData.value.kind === 'aggregator')

const kindItems: { label: string, value: AgentKind, icon: string, hint: string }[] = [
  { label: 'LLM agent', value: 'llm', icon: 'i-ph-robot-bold', hint: 'Calls a model with a prompt' },
  { label: 'Aggregator', value: 'aggregator', icon: 'i-ph-function-bold', hint: 'Combines other agents\' outputs with formulas' },
]

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  // An aggregator is described by its formulas: a description is optional
  return formData.value.name.trim()
    && (aggregator.value || formData.value.description.trim())
    && formData.value.team_id > 0
})

// Methods
function resetForm() {
  formData.value = {
    name: '',
    description: '',
    kind: props.initialKind,
    default_prompt_version_id: null,
    default_model_id: null,
    tag_ids: [],
    team_id: props.initialTeamId || props.availableTeams?.[0]?.id || 0,
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
    const data = { ...formData.value }
    if (aggregator.value) {
      data.default_prompt_version_id = null
      data.default_model_id = null
    }
    emit('submit', data)
    show.value = false
  }
  finally {
    isSubmitting.value = false
  }
}

// Initialize form when component mounts, and on each opening (the initial kind or team may have changed)
onMounted(() => {
  resetForm()
})
watch(() => props.open, (open) => {
  if (open)
    resetForm()
})
</script>

<template>
  <UModal v-model:open="show" :prevent-close="isSubmitting" @after:leave="resetForm">
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-lg font-semibold text-highlighted">
            {{ aggregator ? 'Create New Aggregator' : 'Create New Agent' }}
          </h2>
        </template>

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Basic Information -->
          <div class="grid grid-cols-1 gap-4">
            <UFormField v-if="!lockKind" label="Kind" :hint="kindItems.find(k => k.value === formData.kind)?.hint">
              <UFieldGroup class="w-full">
                <UButton
                  v-for="item in kindItems"
                  :key="item.value"
                  :label="item.label"
                  :icon="item.icon"
                  :variant="formData.kind === item.value ? 'subtle' : 'outline'"
                  color="neutral"
                  class="flex-1 justify-center"
                  :aria-pressed="formData.kind === item.value"
                  @click="() => { formData.kind = item.value }"
                />
              </UFieldGroup>
            </UFormField>

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
              <UFormField label="Description" :hint="aggregator ? 'Optional' : undefined">
                <UTextarea
                  v-model="formData.description"
                  class="w-full"
                  :placeholder="aggregator ? 'What the combined score means' : 'Brief description of the agent\'s purpose'"
                  :rows="3"
                  :required="!aggregator"
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

            <UFormField label="Tags (Optional)">
              <TagsInput v-model="formData.tag_ids" />
            </UFormField>

            <p v-if="aggregator" class="text-sm text-muted">
              Its formulas, and the agents they read, are set in each experiment.
            </p>

            <div v-if="!aggregator">
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

            <div v-if="!aggregator">
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
              {{ aggregator ? 'Create Aggregator' : 'Create Agent' }}
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
