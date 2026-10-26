import type { AgentConfiguration, AgentInputMapping, Experiment, PromptVersion, Variation, VariationDraft, VariationField } from '~/types'
import { mappingSource } from './steps'
import { isMappingComplete, parsePromptVariables } from './utils'

// Past this many experiments at once, ask before starting (each one is a paid run over the whole sample)
export const BATCH_CONFIRM_THRESHOLD = 10

export const VARIATION_FIELDS: { value: VariationField, label: string, icon: string }[] = [
  { value: 'model_id', label: 'Model', icon: 'i-ph-cpu-bold' },
  { value: 'prompt_version_id', label: 'Prompt version', icon: 'i-ph-chat-text-bold' },
  { value: 'temperature', label: 'Temperature', icon: 'i-ph-thermometer-bold' },
]

/** Value of a varied field in the base configuration (a temperature left empty is the model's default: null) */
export function baseValue(config: AgentConfiguration | undefined, field: VariationField): number | null {
  if (field === 'temperature')
    return config?.temperature ?? null
  return (field === 'model_id' ? config?.model_id : config?.prompt_version_id) ?? null
}

/** The values that run on one axis: the base configuration's, then what the variation adds */
export function resolveVariations(
  drafts: readonly VariationDraft[],
  configs: Record<string, AgentConfiguration>,
): Variation[] {
  return drafts.map((draft) => {
    const base = baseValue(configs[draft.step_key], draft.field)
    const added = draft.extras.filter(value => value !== base)
    // A model or prompt not chosen yet has no base value to run
    return { step_key: draft.step_key, field: draft.field, values: base === null && draft.field !== 'temperature' ? added : [base, ...added] }
  })
}

/** Experiments the grid generates: one per combination of values, minus the base one when it already exists */
export function variationCount(variations: readonly Variation[], skipBase = false): number {
  if (variations.length === 0)
    return 0
  const total = variations.reduce((product, v) => product * v.values.length, 1)
  return Math.max(total - (skipBase ? 1 : 0), 0)
}

/**
 * Variables that the prompt versions of a variation have and the step's current prompt does not.
 * They share the step's mappings, so each one needs a source of its own.
 */
export function addedVariables(
  draft: VariationDraft,
  config: AgentConfiguration | undefined,
  promptVersions: readonly PromptVersion[],
): string[] {
  if (draft.field !== 'prompt_version_id')
    return []
  const variablesOf = (id: number | undefined) => parsePromptVariables(promptVersions.find(v => v.id === id)?.variables)
  const own = new Set(variablesOf(config?.prompt_version_id))
  return [...new Set(draft.extras.flatMap(variablesOf).filter(variable => !own.has(variable)))]
}

/** The same, per step (by step key) */
export function addedVariablesByStep(
  drafts: readonly VariationDraft[],
  configs: Record<string, AgentConfiguration>,
  promptVersions: readonly PromptVersion[],
): Record<string, string[]> {
  const byStep: Record<string, string[]> = {}
  for (const draft of drafts) {
    const added = addedVariables(draft, configs[draft.step_key], promptVersions)
    if (added.length > 0)
      byStep[draft.step_key] = [...new Set([...(byStep[draft.step_key] ?? []), ...added])]
  }
  return byStep
}

/** How many of those variables still have no complete mapping */
export function unmappedAddedCount(added: Record<string, readonly string[]>, configs: Record<string, AgentConfiguration>): number {
  return Object.entries(added).reduce((total, [stepKey, variables]) => {
    const mapped = new Set((configs[stepKey]?.input_mappings ?? []).filter(isMappingComplete).map(m => m.variable))
    return total + variables.filter(variable => !mapped.has(variable)).length
  }, 0)
}

/** Why the variations cannot be submitted yet, in words */
export function variationIssues(drafts: readonly VariationDraft[]): string[] {
  const seen = new Set<string>()
  const issues = new Set<string>()
  for (const draft of drafts) {
    const key = `${draft.step_key}:${draft.field}`
    if (seen.has(key))
      issues.add('Two variations change the same field of the same step')
    seen.add(key)
  }
  return [...issues]
}

// --- Is the form still the experiment it was copied from? ---

interface Signature {
  dataset_id: number | null | undefined
  sampling: (number | string | null)[]
  agents: unknown[]
}

function mappingSignature(mappings: readonly { variable: string, source: string, sourceColumn?: string, sourceStep?: string, sourceAgentId?: number, sourceOutput?: string, sourcePath?: string, staticValue?: string }[] | null | undefined) {
  return [...(mappings ?? [])]
    .sort((a, b) => a.variable.localeCompare(b.variable))
    .map(m => [m.variable, m.source, m.sourceColumn ?? '', mappingSource(m as AgentInputMapping) ?? null, m.sourceOutput ?? '', m.sourcePath ?? '', m.staticValue ?? ''])
}

function agentsSignature(steps: { step_key: string, config: AgentConfiguration }[]) {
  return [...steps]
    .sort((a, b) => (a.config.execution_order ?? 0) - (b.config.execution_order ?? 0) || a.step_key.localeCompare(b.step_key, undefined, { numeric: true }))
    .map(({ step_key, config }) => [
      step_key,
      config.prompt_version_id ?? null,
      config.model_id ?? null,
      config.temperature ?? null,
      config.max_tokens ?? null,
      mappingSignature(config.input_mappings),
      (config.formulas ?? []).map(f => [f.name, f.formula]),
    ])
}

/** What an experiment runs, comparable between the form and the experiment it was copied from */
export function formSignature(
  datasetId: number | null | undefined,
  sampling: { sampling_type?: string, sampling_size?: number, sampling_start_row?: number, sampling_end_row?: number, sampling_seed?: number },
  configurations: Record<string, AgentConfiguration>,
): string {
  const signature: Signature = {
    dataset_id: datasetId,
    // A random sample is the same rows only with the same seed
    sampling: [sampling.sampling_type ?? 'all', sampling.sampling_size ?? null, sampling.sampling_start_row ?? null, sampling.sampling_end_row ?? null, sampling.sampling_type === 'random' ? sampling.sampling_seed ?? null : null],
    agents: agentsSignature(Object.entries(configurations)
      .filter(([, config]) => config?.is_active !== false)
      .map(([key, config]) => ({ step_key: key, config }))),
  }
  return JSON.stringify(signature)
}

export function experimentSignature(experiment: Experiment): string {
  return formSignature(
    experiment.dataset_id,
    {
      sampling_type: experiment.sampling_type ?? undefined,
      sampling_size: experiment.sampling_size ?? undefined,
      sampling_start_row: experiment.sampling_start_row ?? undefined,
      sampling_end_row: experiment.sampling_end_row ?? undefined,
      sampling_seed: experiment.sampling_seed ?? undefined,
    },
    Object.fromEntries((experiment.experiment_configs ?? [])
      .filter(config => config.is_active)
      .map(config => [config.step_key, {
        prompt_version_id: config.prompt_version_id ?? undefined,
        model_id: config.model_id ?? undefined,
        temperature: config.temperature ?? undefined,
        max_tokens: config.max_tokens ?? undefined,
        execution_order: config.execution_order,
        input_mappings: config.input_mappings ?? [],
        formulas: config.formulas ?? undefined,
      }])),
  )
}
