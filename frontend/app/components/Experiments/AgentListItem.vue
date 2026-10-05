<script setup lang="ts">
import type { PipelineItem } from '~/composables/useAgentPipeline'
import type { Agent, AgentConfiguration, AgentInputMapping, Model, PromptVersion } from '~/types'

// One agent of the experiment.
// - Alone, it is simply a form: nothing to expand, reorder or switch off
// - In a sequence, it is a row that expands into the same form, with move and remove controls
const props = defineProps<{
  item: PipelineItem
  /** Number of agents in the experiment */
  count: number
  models: readonly Model[]
  promptVersions: readonly PromptVersion[]
  datasetHeaders: readonly string[]
  upstreamAgents: readonly Agent[]
  issues: readonly string[]
}>()

const emit = defineEmits<{
  update: [field: keyof AgentConfiguration, value: unknown]
  setMapping: [mapping: AgentInputMapping]
  openPromptDetails: [promptVersionId: number]
  move: [delta: -1 | 1]
  remove: []
  reset: []
}>()

const open = defineModel<boolean>('open', { default: false })

const single = computed(() => props.count === 1)
const enabled = computed(() => props.item.config.is_active !== false)

const aggregator = computed(() => props.item.agent.kind === 'aggregator')
const icon = computed(() => aggregator.value ? 'i-ph-function-bold' : 'i-ph-ghost-bold')
// An aggregator is summed up by what it outputs
const outputsLabel = computed(() => (props.item.config.formulas ?? []).map(f => f.name).filter(Boolean).join(', '))

const prompt = computed(() => props.promptVersions.find(v => v.id === props.item.config.prompt_version_id))
const promptLabel = computed(() => prompt.value ? `${prompt.value.prompt?.name || 'Unknown'} v${prompt.value.version}` : null)
const model = computed(() => props.models.find(m => m.id === props.item.config.model_id) ?? null)

const issueSummary = computed(() => props.issues.length === 1 ? props.issues[0] : `${props.issues.length} to fix`)
</script>

<template>
  <!-- One agent: a plain form -->
  <section v-if="single" class="rounded-lg border border-default">
    <header class="flex items-start gap-3 px-4 py-3">
      <UIcon :name="icon" class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
      <div class="min-w-0 flex-1">
        <h3 class="truncate text-sm font-semibold text-highlighted">
          {{ item.agent.name }}
        </h3>
        <p v-if="item.team" class="text-xs text-muted">
          {{ item.team.name }}
        </p>
        <p v-if="item.agent.description" class="mt-1 text-sm text-muted text-pretty line-clamp-2" :title="item.agent.description">
          {{ item.agent.description }}
        </p>
      </div>
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        icon="i-ph-repeat-bold"
        @click="emit('remove')"
      >
        Change agent
      </UButton>
    </header>

    <div class="border-t border-default bg-elevated/30 px-4 py-4">
      <ExperimentsAggregatorSettings
        v-if="aggregator"
        :config="item.config"
        :dataset-headers="datasetHeaders"
        :upstream-agents="upstreamAgents"
        @update="(field, value) => emit('update', field, value)"
        @set-mapping="mapping => emit('setMapping', mapping)"
      />
      <ExperimentsAgentSettings
        v-else
        :config="item.config"
        :models="models"
        :prompt-versions="promptVersions"
        :dataset-headers="datasetHeaders"
        :upstream-agents="upstreamAgents"
        @update="(field, value) => emit('update', field, value)"
        @set-mapping="mapping => emit('setMapping', mapping)"
        @open-prompt-details="id => emit('openPromptDetails', id)"
      />
      <div class="mt-4">
        <UButton color="neutral" variant="ghost" size="sm" icon="i-ph-arrow-counter-clockwise-bold" @click="emit('reset')">
          Reset to agent defaults
        </UButton>
      </div>
    </div>
  </section>

  <!-- Several agents: an expandable row -->
  <div v-else class="group/row relative">
    <UCollapsible v-model:open="open" class="group/agent">
      <!-- Native button: a full-width row shouldn't inherit the press scale of UButton. Hover is instant on purpose (frequent). -->
      <button
        type="button"
        class="flex h-14 w-full items-center gap-3 ps-8 pe-14 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
        :class="{ 'opacity-60': !enabled }"
      >
        <UIcon
          name="i-ph-caret-right-bold"
          class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none group-data-[state=open]/agent:rotate-90"
          aria-hidden="true"
        />
        <span
          class="flex size-6 shrink-0 items-center justify-center rounded-full border border-default text-xs font-medium text-toned tabular-nums"
        >
          <span class="sr-only">Step </span>{{ item.position }}
        </span>

        <span class="min-w-0 flex-1">
          <span class="flex items-baseline gap-2 min-w-0">
            <span class="truncate text-sm font-medium text-highlighted">{{ item.agent.name }}</span>
            <span v-if="item.team" class="hidden shrink-0 text-xs text-muted sm:inline">{{ item.team.name }}</span>
          </span>
          <span class="mt-0.5 block truncate text-xs text-muted">
            <template v-if="!enabled">Skipped in this run</template>
            <template v-else-if="aggregator">
              <span class="font-mono">{{ outputsLabel || 'No output yet' }}</span>
            </template>
            <template v-else-if="promptLabel || model">
              {{ promptLabel }}<span v-if="promptLabel && model" aria-hidden="true"> · </span><ModelsLabel v-if="model" :name="model.name" :provider="model.provider" />
            </template>
            <template v-else>Not configured</template>
          </span>
        </span>

        <span
          v-if="enabled && issues.length > 0"
          class="hidden h-5 shrink-0 items-center gap-1 rounded-full bg-warning/10 px-2 text-xs font-medium text-warning sm:inline-flex"
          :title="issues.join('\n')"
        >
          <UIcon name="i-ph-warning-bold" class="size-3 shrink-0" aria-hidden="true" />
          <span class="leading-none">{{ issueSummary }}</span>
        </span>
      </button>

      <template #content>
        <div class="border-t border-default bg-elevated/30 px-4 py-4 ps-15">
          <ExperimentsAggregatorSettings
            v-if="aggregator"
            :config="item.config"
            :dataset-headers="datasetHeaders"
            :upstream-agents="upstreamAgents"
            @update="(field, value) => emit('update', field, value)"
            @set-mapping="mapping => emit('setMapping', mapping)"
          />
          <ExperimentsAgentSettings
            v-else
            :config="item.config"
            :models="models"
            :prompt-versions="promptVersions"
            :dataset-headers="datasetHeaders"
            :upstream-agents="upstreamAgents"
            @update="(field, value) => emit('update', field, value)"
            @set-mapping="mapping => emit('setMapping', mapping)"
            @open-prompt-details="id => emit('openPromptDetails', id)"
          />
          <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
            <USwitch
              :model-value="enabled"
              label="Run this agent"
              size="sm"
              @update:model-value="(value: boolean) => emit('update', 'is_active', value)"
            />
            <UButton color="neutral" variant="ghost" size="sm" icon="i-ph-arrow-counter-clockwise-bold" @click="emit('reset')">
              Reset to agent defaults
            </UButton>
          </div>
        </div>
      </template>
    </UCollapsible>

    <!-- Outside the trigger so the buttons aren't nested in it -->
    <button
      type="button"
      :data-drag-handle="item.agent.id"
      :aria-label="`Reorder ${item.agent.name}: drag, or use the up and down arrow keys`"
      class="absolute start-1 top-0 flex h-14 w-6 cursor-grab items-center justify-center rounded text-dimmed opacity-0 outline-none transition-opacity duration-150 hover:text-toned focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-inverted group-hover/row:opacity-100 active:cursor-grabbing"
      @keydown.up.prevent="emit('move', -1)"
      @keydown.down.prevent="emit('move', 1)"
    >
      <UIcon name="i-ph-dots-six-vertical-bold" class="size-4" aria-hidden="true" />
    </button>

    <div class="absolute end-2 top-0 flex h-14 items-center gap-0.5">
      <UButton
        color="neutral"
        variant="ghost"
        size="sm"
        icon="i-ph-x-bold"
        :aria-label="`Remove ${item.agent.name}`"
        @click="emit('remove')"
      />
    </div>
  </div>
</template>
