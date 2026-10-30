<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Agent, Model, PromptVersion } from '~/types'

// One agent in a slideover, edited in place and saved with one button, so the list stays a table to scan.
// - j / k move through the agents the table shows; they wait while there are unsaved edits
// - Closing the panel with unsaved edits asks first: they are dropped with it
const props = withDefaults(defineProps<{
  agent: Agent | null
  /** Position among the agents currently shown */
  index: number
  total: number
  promptVersions?: readonly PromptVersion[]
  models?: readonly Model[]
}>(), {
  promptVersions: () => [],
  models: () => [],
})

const emit = defineEmits<{
  saved: []
  delete: [agent: Agent]
  navigate: [delta: number]
}>()

const open = defineModel<boolean>('open', { default: false })

const { showUpdateSuccess, showUpdateError } = useStandardToast()
const { updateAgent } = useAgents()
const { refreshTags } = useTags()
const { formatDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

interface AgentForm {
  name: string
  description: string
  default_prompt_version_id: number | null
  default_model_id: number | null
  tag_ids: number[]
}

function snapshot(agent: Agent | null): AgentForm {
  return {
    name: agent?.name ?? '',
    description: agent?.description ?? '',
    default_prompt_version_id: agent?.default_prompt_version_id ?? null,
    default_model_id: agent?.default_model_id ?? null,
    tag_ids: (agent?.tags ?? []).map(tag => tag.id),
  }
}

const formId = useId()
const nameError = ref('')
const saving = ref(false)

const baseline = ref<AgentForm>(snapshot(props.agent))
const form = ref<AgentForm>(structuredClone(toRaw(baseline.value)))

// Tags have no order of their own
const sameTags = (a: number[], b: number[]) => a.length === b.length && a.every(id => b.includes(id))

const dirty = computed(() => {
  const { tag_ids: tags, ...fields } = form.value
  return (Object.keys(fields) as (keyof typeof fields)[]).some(key => fields[key] !== baseline.value[key])
    || !sameTags(tags, baseline.value.tag_ids)
})

function reset() {
  baseline.value = snapshot(props.agent)
  form.value = structuredClone(toRaw(baseline.value))
  nameError.value = ''
}

// A refresh (after saving) moves the baseline; pending edits are kept unless another agent is shown
watch(() => props.agent, (agent, previous) => {
  const wasDirty = dirty.value
  baseline.value = snapshot(agent)
  if (agent?.id !== previous?.id || !wasDirty)
    form.value = structuredClone(toRaw(baseline.value))
})

watch(open, (isOpen) => {
  if (isOpen)
    reset()
})

watch(() => form.value.name, () => {
  nameError.value = ''
})

async function save() {
  if (!canEdit.value || !dirty.value || saving.value || !props.agent)
    return

  const name = form.value.name.trim()
  if (!name) {
    nameError.value = 'Give the agent a name'
    document.getElementById(`${formId}-name`)?.focus()
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
    showUpdateSuccess('Agent', { description: name })
    refreshTags()
    emit('saved')
  }
  else {
    showUpdateError('Agent', result.error)
  }
}

const aggregator = computed(() => props.agent?.kind === 'aggregator')

// Esc, a click outside and the close button all land here
const confirmDiscard = ref(false)
function onOpenChange(value: boolean) {
  if (!value && dirty.value && canEdit.value)
    confirmDiscard.value = true
  else
    open.value = value
}

function discardAndClose() {
  confirmDiscard.value = false
  open.value = false
}

// Typing in a field is left alone: these only fire outside inputs
defineShortcuts({
  j: () => open.value && !dirty.value && emit('navigate', 1),
  k: () => open.value && !dirty.value && emit('navigate', -1),
})
</script>

<template>
  <USlideover
    :open="open"
    :title="agent?.name ?? 'Agent'"
    :description="agent ? `${index + 1} of ${total.toLocaleString('en-US')}` : undefined"
    :ui="{ content: 'max-w-md' }"
    @update:open="onOpenChange"
  >
    <template #body>
      <form
        v-if="agent"
        :id="formId"
        class="flex flex-col gap-5"
        @submit.prevent="save"
        @keydown.meta.enter.prevent="save"
        @keydown.ctrl.enter.prevent="save"
      >
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
          <AgentsKindBadge :kind="agent.kind" />
          <span class="text-xs text-muted tabular-nums">
            Created {{ formatDate(agent.created_at) }}
          </span>
          <UIPerson v-if="agent.author" :person="agent.author" label="Created by" class="text-xs text-muted" />
          <span v-if="dirty" class="inline-flex items-center gap-1 text-xs text-warning">
            <span class="size-1.5 rounded-full bg-warning" aria-hidden="true" />
            Unsaved
          </span>
        </div>

        <UFormField label="Name" :error="nameError || undefined" required>
          <UInput :id="`${formId}-name`" v-model="form.name" class="w-full" autocomplete="off" :disabled="!canEdit" />
        </UFormField>

        <UFormField label="Description">
          <UTextarea
            v-model="form.description"
            class="w-full"
            :rows="2"
            autoresize
            :maxrows="8"
            :disabled="!canEdit"
            placeholder="What this agent is for"
          />
        </UFormField>

        <UFormField label="Tags">
          <TagsInput v-model="form.tag_ids" />
        </UFormField>

        <p v-if="aggregator" class="flex items-start gap-2 rounded-lg border border-default bg-elevated/30 px-3 py-2.5 text-sm text-muted text-pretty">
          <UIcon name="i-ph-function-bold" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          An aggregator combines other agents’ outputs with formulas, set in each experiment. It has no prompt or model.
        </p>

        <template v-else>
          <UFormField label="Default prompt version">
            <PromptsSelect
              v-model="form.default_prompt_version_id"
              :prompt-versions="promptVersions"
              clearable
              :disabled="!canEdit"
              placeholder="No default prompt"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Default model">
            <ModelsSelect
              v-model="form.default_model_id"
              :models="models"
              clearable
              :disabled="!canEdit"
              placeholder="No default model"
              class="w-full"
            />
          </UFormField>
        </template>
      </form>
    </template>

    <template #footer>
      <div class="flex w-full items-center gap-2">
        <div class="flex items-center gap-1">
          <UTooltip text="Previous agent" :kbds="['k']">
            <UButton
              icon="i-ph-caret-up-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Previous agent"
              :disabled="index <= 0 || dirty"
              @click="emit('navigate', -1)"
            />
          </UTooltip>
          <UTooltip text="Next agent" :kbds="['j']">
            <UButton
              icon="i-ph-caret-down-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Next agent"
              :disabled="index >= total - 1 || dirty"
              @click="emit('navigate', 1)"
            />
          </UTooltip>
        </div>

        <UIGuardedButton
          v-if="agent"
          icon="i-ph-trash-bold"
          label="Delete"
          color="error"
          variant="ghost"
          size="sm"
          @click="emit('delete', agent)"
        />

        <div class="ms-auto flex items-center gap-2">
          <UButton
            v-if="canEdit"
            type="button"
            color="neutral"
            variant="ghost"
            size="sm"
            :disabled="!dirty || saving"
            @click="reset"
          >
            Discard
          </UButton>
          <UIGuardedButton
            type="submit"
            :form="formId"
            size="sm"
            :disabled="!dirty"
            :loading="saving"
            aria-keyshortcuts="Meta+Enter Control+Enter"
            title="Save (⌘↵)"
          >
            Save
          </UIGuardedButton>
        </div>
      </div>
    </template>
  </USlideover>

  <BaseConfirmDialog
    v-model:open="confirmDiscard"
    title="Discard changes?"
    message="Your unsaved edits to this agent are lost when the panel closes."
    confirm-label="Discard changes"
    cancel-label="Keep editing"
    variant="warning"
    @confirm="discardAndClose"
  />
</template>
