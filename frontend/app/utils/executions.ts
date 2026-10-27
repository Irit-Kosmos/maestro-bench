// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

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
