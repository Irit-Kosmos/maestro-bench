<script setup lang="ts">
import type { Agent, CreateAgentTeamForm } from '~/types'

interface Props {
  open?: boolean
  availableAgents?: readonly Agent[]
  /** The request is under way: the dialog stays open, and keeps the form if it fails */
  loading?: boolean
}

interface Emits {
  'update:open': [value: boolean]
  'submit': [data: CreateAgentTeamForm]
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  availableAgents: () => [],
  loading: false,
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

// Computed
const formValid = computed(() => {
  return !!formData.value.name.trim()
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
  show.value = false
}

// The page closes the dialog once the team is created
function handleSubmit() {
  if (!formValid.value || props.loading)
    return
  emit('submit', { ...formData.value })
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
</script>

<template>
  <UModal v-model:open="show" :dismissible="!loading" @after:leave="resetForm">
    <template #content>
      <UCard>
        <template #header>
          <h2 class="text-base font-semibold text-highlighted">
            New team
          </h2>
        </template>

        <form class="space-y-4" @submit.prevent="handleSubmit">
          <UFormField label="Name" required>
            <UInput
              v-model="formData.name"
              class="w-full"
              placeholder="e.g. Math assessment"
              autofocus
            />
          </UFormField>

          <UFormField label="Description">
            <UTextarea
              v-model="formData.description"
              :rows="2"
              class="w-full"
              placeholder="What this team does"
            />
          </UFormField>

          <UFormField
            v-if="availableAgents.length"
            label="Agents"
            description="Move existing agents into this team now, or add them later."
          >
            <ul class="max-h-52 overflow-y-auto divide-y divide-default rounded-lg border border-default">
              <li v-for="agent in availableAgents" :key="agent.id" class="px-3 py-2">
                <UCheckbox
                  :model-value="formData.agent_ids?.includes(agent.id)"
                  :label="agent.name"
                  :description="agent.description || undefined"
                  @update:model-value="toggleAgent(agent.id)"
                />
              </li>
            </ul>
          </UFormField>

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
              Create team
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
