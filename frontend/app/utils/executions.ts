import type { GroupSummaryPart } from './groups'
import type { AgentExecutionSnapshot } from '~/types'

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
