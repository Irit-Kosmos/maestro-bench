import type { FilterSpec } from './filters'
import type { GroupSummaryPart } from './groups'
import type { AgentExecutionSnapshot, ExecutionListItem } from '~/types'
import { byOrder } from './filters'

/** The step of the experiment a snapshot ran: its agent for the snapshots made before agents could run twice */
export function snapshotStep(snapshot: Pick<AgentExecutionSnapshot, 'step_key' | 'agent_id'>): string | undefined {
  return snapshot.step_key ?? (snapshot.agent_id === null ? undefined : String(snapshot.agent_id))
}

/** Stopped by someone or by a restart rather than by a problem of its own, so it is never a failure. */
const isStopped = (status?: string | null) => status === 'cancelled' || status === 'interrupted'

/** Whether an execution is a problem to look into: it failed, or went on with failed rows. Cancelling is a choice, and a restart is not its fault, so neither is. */
export function hasFailures(execution: { status?: string | null, rows_failed?: number | null }): boolean {
  return !isStopped(execution.status) && (execution.status === 'failed' || (execution.rows_failed ?? 0) > 0)
}

/**
 * What stands out in a group of runs: how many are going and how many went wrong, nothing when all is well.
 * Reads a failure with `hasFailures`, so the count matches the failures filter and the dashboard.
 */
export function runsSummary(runs: readonly { status?: string | null, rows_failed?: number | null }[]): GroupSummaryPart[] {
  const running = runs.filter(run => run.status === 'running').length
  const failed = runs.filter(hasFailures).length
  return [
    ...(running ? [{ label: `${running} running`, class: 'text-warning' }] : []),
    ...(failed ? [{ label: `${failed} failed`, class: 'text-error' }] : []),
  ]
}

/** Whether an analysis can read the execution: it ended well and left its results behind. */
export function isAnalyzable(execution: Pick<ExecutionListItem, 'status' | 'has_results'>): boolean {
  return execution.status === 'completed' && execution.has_results
}

const FAILURES = {
  failed: { label: 'Failed or with failed rows', icon: 'i-ph-warning-bold', iconClass: 'text-error' },
  clean: { label: 'No failures' },
} as const

/** Same reading as the dashboard's count of executions with failures. */
export function executionFailuresFilter(): FilterSpec<ExecutionListItem> {
  return {
    key: 'failures',
    label: 'Failures',
    icon: 'i-ph-warning-bold',
    multiple: false,
    value: execution => hasFailures(execution) ? 'failed' : 'clean',
    present: value => FAILURES[value as keyof typeof FAILURES] ?? { label: String(value) },
    compare: byOrder(Object.keys(FAILURES)),
  }
}

/** The models of the agents. An execution can use several, so "is all of" is offered. */
export function executionModelsFilter(): FilterSpec<ExecutionListItem> {
  return {
    key: 'model',
    label: 'Model',
    icon: 'i-ph-cpu-bold',
    plural: 'models',
    multiValued: true,
    searchPlaceholder: 'Search a model…',
    // Aggregators have no model
    value: execution => [...new Set(execution.agents.filter(agent => agent.model).map(agent => agent.model))],
  }
}

/** The experiment an execution belongs to, picked by id and read by name. */
export function executionExperimentFilter(items: () => readonly ExecutionListItem[]): FilterSpec<ExecutionListItem> {
  return {
    key: 'experiment',
    label: 'Experiment',
    icon: 'i-ph-flask-bold',
    plural: 'experiments',
    searchPlaceholder: 'Search an experiment…',
    value: execution => execution.experiment_id,
    present: (id) => {
      const found = items().find(execution => execution.experiment_id === Number(id))
      return { label: found?.experiment_name ?? `Experiment #${id}`, icon: 'i-ph-flask-bold' }
    },
  }
}

/** The batch an execution's experiment belongs to, picked by id and read by name. */
export function executionBatchFilter(items: () => readonly ExecutionListItem[]): FilterSpec<ExecutionListItem> {
  return {
    key: 'batch',
    label: 'Batch',
    icon: 'i-ph-arrows-split-bold',
    plural: 'batches',
    searchPlaceholder: 'Search a batch…',
    value: execution => execution.batch_id,
    present: (id) => {
      const found = items().find(execution => execution.batch_id === Number(id))
      return { label: found?.batch_name ?? `Batch #${id}`, icon: 'i-ph-arrows-split-bold' }
    },
  }
}
