<script setup lang="ts">
import type { Agent, AgentTeam, Model, PromptVersion } from '~/types'

// An agent as a list row that expands into an inline editor.
// - The collapsed row shows what the agent is; the panel edits it in place, saved with one button
// - Unsaved edits survive collapsing (a dot on the row says they are pending)
const props = withDefaults(defineProps<{
  agent: Agent
  teams?: readonly AgentTeam[]
  promptVersions?: readonly PromptVersion[]
  models?: readonly Model[]
}>(), {
  teams: () => [],
  promptVersions: () => [],
  models: () => [],
})

const emit = defineEmits<{
  saved: []
  delete: [agent: Agent]
}>()

const open = defineModel<boolean>('open', { default: false })

const toast = useToast()
const { updateAgent } = useAgents()

interface AgentForm {
  name: string
  description: string
  team_id: number
  default_prompt_version_id: number | null
  default_model_id: number | null
}

function snapshot(agent: Agent): AgentForm {
  return {
    name: agent.name,
    description: agent.description ?? '',
    team_id: agent.team_id,
    default_prompt_version_id: agent.default_prompt_version_id,
    default_model_id: agent.default_model_id,
  }
}

const baseline = ref<AgentForm>(snapshot(props.agent))
const form = ref<AgentForm>({ ...baseline.value })

const dirty = computed(() => (Object.keys(form.value) as (keyof AgentForm)[])
  .some(key => form.value[key] !== baseline.value[key]))

// A refresh (after saving this or another agent) moves the baseline; pending edits are kept
watch(() => props.agent, (agent) => {
  const wasDirty = dirty.value
  baseline.value = snapshot(agent)
  if (!wasDirty)
    form.value = { ...baseline.value }
})

const ids = useId()
const nameError = ref('')
const saving = ref(false)

watch(() => form.value.name, () => {
  nameError.value = ''
})

function discard() {
  form.value = { ...baseline.value }
  nameError.value = ''
}

async function save() {
  if (!dirty.value || saving.value)
    return

  const name = form.value.name.trim()
  if (!name) {
    nameError.value = 'Give the agent a name'
    document.getElementById(`${ids}-name`)?.focus()
    return
  }

  saving.value = true
  const result = await updateAgent(props.agent.id, {
    ...form.value,
    name,
    description: form.value.description.trim(),
  })
  saving.value = false

  if (result.success) {
    toast.add({ title: 'Agent saved', description: name, color: 'success', icon: 'i-lucide:check' })
    emit('saved')
  }
  else {
    toast.add({ title: 'Could not save', description: result.error || 'Failed to update agent', color: 'error', icon: 'i-lucide:x' })
  }
}

// The API returns ids only, so the row summary resolves names from the lists
const savedPromptLabel = computed(() => {
  const version = props.promptVersions.find(v => v.id === props.agent.default_prompt_version_id)
  return version ? `${version.prompt?.name || 'Unknown'} v${version.version}` : null
})
const savedModelName = computed(() => props.models.find(m => m.id === props.agent.default_model_id)?.name ?? null)

const teamItems = computed(() => props.teams.map(team => ({ label: team.name, value: team.id })))

const promptVersionItems = computed(() => [
  { label: 'No default prompt', value: null },
  ...props.promptVersions.map(version => ({
    label: `${version.prompt?.name || 'Unknown'} v${version.version}`,
    value: version.id,
  })),
])

// Keep the current model selectable even if it was deactivated since
const modelItems = computed(() => [
  { label: 'No default model', value: null },
  ...props.models
    .filter(model => model.is_active || model.id === baseline.value.default_model_id)
    .map(model => ({ label: `${model.name} (${model.provider})`, value: model.id })),
])
</script>

<template>
  <UCollapsible v-model:open="open" class="group/agent">
    <!-- Native button: a full-width row shouldn't inherit the press scale of UButton. Hover is instant on purpose (frequent). -->
    <button
      type="button"
      class="flex w-full items-center gap-3 px-4 py-3 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary"
    >
      <UIcon
        name="i-lucide-chevron-right"
        class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none group-data-[state=open]/agent:rotate-90"
        aria-hidden="true"
      />

      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 min-w-0">
          <span class="truncate text-sm font-medium text-highlighted">{{ agent.name }}</span>
          <span
            v-if="dirty"
            class="inline-flex shrink-0 items-center gap-1 text-xs text-warning"
          >
            <span class="size-1.5 rounded-full bg-warning" aria-hidden="true" />
            Unsaved
          </span>
        </div>
        <p v-if="agent.description" class="mt-0.5 truncate text-sm text-muted" :title="agent.description">
          {{ agent.description }}
        </p>
      </div>

      <div class="hidden md:flex flex-col items-end gap-0.5 shrink-0 text-xs text-toned">
        <span v-if="savedPromptLabel" class="inline-flex items-center gap-1">
          <UIcon name="i-lucide-message-square-text" class="size-3 text-muted" aria-hidden="true" />
          {{ savedPromptLabel }}
        </span>
        <span v-if="savedModelName" class="inline-flex items-center gap-1">
          <UIcon name="i-lucide-cpu" class="size-3 text-muted" aria-hidden="true" />
          {{ savedModelName }}
        </span>
      </div>
    </button>

    <template #content>
      <form
        class="border-t border-default bg-elevated/30 px-4 py-4 ps-11"
        @submit.prevent="save"
        @keydown.meta.enter.prevent="save"
        @keydown.ctrl.enter.prevent="save"
      >
        <div class="grid gap-4 md:grid-cols-2">
          <UFormField label="Name" :error="nameError || undefined" required>
            <UInput :id="`${ids}-name`" v-model="form.name" class="w-full" autocomplete="off" />
          </UFormField>

          <UFormField label="Team">
            <USelect v-model="form.team_id" :items="teamItems" class="w-full" />
          </UFormField>

          <UFormField label="Description" class="md:col-span-2">
            <UTextarea
              v-model="form.description"
              class="w-full"
              :rows="2"
              autoresize
              :maxrows="6"
              placeholder="What this agent is for"
            />
          </UFormField>

          <UFormField label="Default prompt version">
            <USelect v-model="form.default_prompt_version_id" :items="promptVersionItems" class="w-full" />
          </UFormField>

          <UFormField label="Default model">
            <USelect v-model="form.default_model_id" :items="modelItems" class="w-full" />
          </UFormField>
        </div>

        <div class="mt-4 flex items-center gap-2">
          <UButton
            type="button"
            color="error"
            variant="ghost"
            size="sm"
            icon="i-lucide-trash-2"
            @click="emit('delete', agent)"
          >
            Delete
          </UButton>

          <div class="ms-auto flex items-center gap-2">
            <UButton
              type="button"
              color="neutral"
              variant="ghost"
              size="sm"
              :disabled="!dirty || saving"
              @click="discard"
            >
              Discard
            </UButton>
            <UButton
              type="submit"
              size="sm"
              :disabled="!dirty"
              :loading="saving"
              aria-keyshortcuts="Meta+Enter Control+Enter"
              title="Save (⌘↵)"
            >
              Save changes
            </UButton>
          </div>
        </div>
      </form>
    </template>
  </UCollapsible>
</template>
