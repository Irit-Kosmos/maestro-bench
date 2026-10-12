<script setup lang="ts">
import type { AgentKind, CreateAgentForm, Model, PromptVersion } from '~/types'

interface Props {
  open?: boolean
  availablePromptVersions?: readonly PromptVersion[]
  availableModels?: readonly Model[]
  /** Kind selected when the modal opens */
  initialKind?: AgentKind
  /** Hides the kind switch: the modal only creates `initialKind` agents */
  lockKind?: boolean
  /** Name filled in when the modal opens */
  initialName?: string
  /** The request is under way: the dialog stays open, and keeps the form if it fails */
  loading?: boolean
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateAgentForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  availablePromptVersions: () => [],
  availableModels: () => [],
  initialKind: 'llm',
  lockKind: false,
  initialName: '',
  loading: false,
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
  tag_ids: [],
})

const aggregator = computed(() => formData.value.kind === 'aggregator')

const kindItems: { label: string, value: AgentKind, icon: string, hint: string }[] = [
  { label: 'LLM agent', value: 'llm', icon: 'i-ph-ghost-bold', hint: 'Calls a model with a prompt' },
  { label: 'Aggregator', value: 'aggregator', icon: 'i-ph-function-bold', hint: 'Combines other agents’ outputs with formulas' },
]

// Computed
const formValid = computed(() => !!formData.value.name.trim())

// Methods
function resetForm() {
  formData.value = {
    name: props.initialName,
    description: '',
    kind: props.initialKind,
    default_prompt_version_id: null,
    default_model_id: null,
    tag_ids: [],
  }
}

function handleCancel() {
  show.value = false
}

// The page closes the dialog once the agent is created
function handleSubmit() {
  if (!formValid.value || props.loading)
    return

  const data = { ...formData.value }
  if (aggregator.value) {
    data.default_prompt_version_id = null
    data.default_model_id = null
  }
  emit('submit', data)
}

// Initialize form when component mounts, and on each opening (the initial kind may have changed)
onMounted(() => {
  resetForm()
})
watch(() => props.open, (open) => {
  if (open)
    resetForm()
})
</script>

<template>
  <UModal
    v-model:open="show"
    :title="aggregator ? 'New aggregator' : 'New agent'"
    :description="aggregator ? 'Combine the outputs of other agents with formulas.' : 'Name the agent and choose its default prompt and model.'"
    :dismissible="!loading"
    @after:leave="resetForm"
  >
    <template #content>
      <UCard class="overflow-y-auto">
        <template #header>
          <h2 class="text-base font-semibold text-highlighted">
            {{ aggregator ? 'New aggregator' : 'New agent' }}
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

            <UFormField label="Name" required>
              <UInput
                v-model="formData.name"
                class="w-full"
                :placeholder="aggregator ? 'e.g. Weighted score' : 'e.g. Grader'"
                autofocus
              />
            </UFormField>

            <UFormField label="Description">
              <UTextarea
                v-model="formData.description"
                class="w-full"
                :placeholder="aggregator ? 'What the combined score means' : 'What this agent is for'"
                :rows="2"
              />
            </UFormField>

            <UFormField label="Tags">
              <TagsInput v-model="formData.tag_ids" />
            </UFormField>

            <p v-if="aggregator" class="text-sm text-muted">
              Its formulas, and the agents they read, are set in each experiment.
            </p>

            <div v-if="!aggregator">
              <UFormField label="Default prompt version">
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
              <UFormField label="Default model">
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
          <div class="flex gap-2 justify-end pt-4 border-t border-default">
            <UButton
              type="button"
              variant="outline"
              color="neutral"
              :disabled="loading"
              @click="handleCancel"
            >
              Cancel
            </UButton>
            <UButton
              type="submit"
              variant="solid"
              color="primary"
              :disabled="!formValid"
              :loading="loading"
            >
              {{ aggregator ? 'Create aggregator' : 'Create agent' }}
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
