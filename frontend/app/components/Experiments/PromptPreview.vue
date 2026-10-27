<script setup lang="ts">
import type { StepRef } from '~/composables/useAgentPipeline'
import type { AgentInputMapping, PromptVersion } from '~/types'
import { watchDebounced } from '@vueuse/core'

// The prompt an agent runs, next to where its variables get their values: as written, with the variable under
// the pointer picked out, or as the model receives it for one row of the dataset, each value picked out.
const props = defineProps<{
  version: PromptVersion | undefined
  variables: readonly string[]
  mappings: readonly AgentInputMapping[] | undefined
  /** Steps that run before this one, for the outputs a variable may read */
  upstreamSteps: readonly StepRef[]
  /** Variable under the pointer in the mappings */
  active?: string | null
  /** Tighter type, for a side panel */
  compact?: boolean
}>()

const ids = useId()
const { renderPrompts } = usePrompts()
const rows = inject(DATASET_SAMPLE, ref([]))

// Closed by default: the mappings above are what needs setting, the prompt is there to check them
const open = ref(false)
const view = ref<'template' | 'rendered'>('template')
const rowIndex = ref(0)

// Without a dataset there is no row to render with
watch(() => rows.value.length, (count) => {
  if (rowIndex.value >= count)
    rowIndex.value = 0
  if (count === 0)
    view.value = 'template'
})

function step(by: number) {
  const count = rows.value.length
  rowIndex.value = (rowIndex.value + by + count) % count
}

const values = computed(() => {
  const row = rows.value[rowIndex.value]
  return row ? previewValues(props.mappings, props.variables, row, props.upstreamSteps) : null
})

const rendered = ref<{ system: string, user: string } | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)

// Only the latest request may fill the preview: the values change faster than the backend answers
let latest = 0

async function render() {
  if (!open.value || view.value !== 'rendered' || !values.value || !props.version)
    return
  const request = ++latest
  loading.value = true
  const result = await renderPrompts({
    system_prompt: props.version.system_prompt,
    user_prompt: props.version.user_prompt,
    variables: markValues(values.value),
  })
  if (request !== latest)
    return
  loading.value = false
  rendered.value = result.success ? result.data : null
  error.value = result.success ? null : result.error
}

watchDebounced([open, view, values, () => props.version?.system_prompt, () => props.version?.user_prompt], render, { debounce: 200, immediate: true })

const segmentClass = 'h-6 rounded-sm px-2.5 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-inverted aria-disabled:cursor-not-allowed aria-disabled:opacity-50'
</script>

<template>
  <section v-if="version && variables.length > 0" :aria-labelledby="`${ids}-title`">
    <div class="flex min-h-7 items-center justify-between gap-2">
      <h4 :id="`${ids}-title`" class="font-medium text-highlighted" :class="compact ? 'text-xs' : 'text-sm'">
        <!-- Native button: hover is instant on purpose, the caret alone moves -->
        <button
          type="button"
          class="-ms-1 inline-flex items-center gap-1 rounded-sm px-1 outline-none hover:text-highlighted focus-visible:outline-2 focus-visible:outline-inverted"
          :aria-expanded="open"
          :aria-controls="`${ids}-content`"
          @click="open = !open"
        >
          <UIcon
            name="i-ph-caret-right-bold"
            class="size-3.5 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none"
            :class="open && 'rotate-90'"
            aria-hidden="true"
          />
          Prompt
        </button>
      </h4>

      <div v-if="open" class="flex items-center gap-2">
        <div v-if="view === 'rendered' && rows.length > 1" class="flex items-center">
          <UButton type="button" icon="i-ph-caret-left-bold" color="neutral" variant="ghost" size="xs" aria-label="Previous row" @click="step(-1)" />
          <span class="text-xs text-muted tabular-nums">Row {{ rowIndex + 1 }} of {{ rows.length }}</span>
          <UButton type="button" icon="i-ph-caret-right-bold" color="neutral" variant="ghost" size="xs" aria-label="Next row" @click="step(1)" />
        </div>

        <div role="group" aria-label="Show the prompt" class="inline-flex rounded-md bg-elevated p-0.5">
          <button
            type="button"
            :class="[segmentClass, view === 'template' ? 'bg-default text-highlighted shadow-xs' : 'text-muted hover:text-highlighted']"
            :aria-pressed="view === 'template'"
            @click="view = 'template'"
          >
            Template
          </button>
          <button
            type="button"
            :class="[segmentClass, view === 'rendered' ? 'bg-default text-highlighted shadow-xs' : 'text-muted hover:text-highlighted']"
            :aria-pressed="view === 'rendered'"
            :aria-disabled="rows.length === 0"
            :aria-describedby="rows.length === 0 ? `${ids}-hint` : undefined"
            @click="rows.length > 0 && (view = 'rendered')"
          >
            Preview
          </button>
        </div>
      </div>
    </div>

    <div v-if="open" :id="`${ids}-content`" class="enter-soft">
      <p :id="`${ids}-hint`" class="mt-0.5 text-muted" :class="compact ? 'text-xs' : 'text-sm'">
        {{ view === 'template' ? 'Hover or focus a variable above to find it in the prompt.' : 'What the model receives for this row.' }}
        <template v-if="rows.length === 0">
          Choose a dataset to preview the prompt with one of its rows.
        </template>
      </p>

      <div class="space-y-4 overflow-y-auto" :class="compact ? 'mt-2 max-h-64' : 'mt-3 max-h-80'">
        <template v-if="view === 'template'">
          <PromptContentDisplay v-if="version.system_prompt" label="System prompt" :content="version.system_prompt" :variables="variables" :active="active" />
          <PromptContentDisplay v-if="version.user_prompt" label="User prompt" :content="version.user_prompt" :variables="variables" :active="active" />
        </template>

        <template v-else-if="rendered && values">
          <PromptRenderedDisplay v-if="rendered.system" label="System prompt" :text="rendered.system" :values="values" :active="active" />
          <PromptRenderedDisplay v-if="rendered.user" label="User prompt" :text="rendered.user" :values="values" :active="active" />
        </template>

        <p v-else-if="error" class="inline-flex items-center gap-1.5 text-sm text-warning">
          <UIcon name="i-ph-warning-bold" class="size-3.5 shrink-0" aria-hidden="true" />
          {{ error }}
        </p>
        <p v-else class="text-sm text-muted" role="status">
          {{ loading ? 'Rendering…' : 'Nothing to show.' }}
        </p>
      </div>
    </div>
  </section>
</template>
