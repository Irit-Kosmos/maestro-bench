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

import type { Workspace, WorkspaceRole } from '~/types'

const RANK: Record<WorkspaceRole, number> = { viewer: 0, editor: 1, owner: 2 }

/**
 * Whether the user's role in a workspace is at least `needed`. An archived workspace is read-only for
 * everyone: only reading (`viewer`) is left in it.
 */
export function canIn(workspace: Pick<Workspace, 'role' | 'archived'> | null | undefined, needed: WorkspaceRole): boolean {
  if (!workspace)
    return false
  if (needed !== 'viewer' && workspace.archived)
    return false
  return RANK[workspace.role] >= RANK[needed]
}

/** Why the user cannot do what needs `needed`, in words for a tooltip; null when they can. */
export function denialReason(workspace: Pick<Workspace, 'role' | 'archived'> | null | undefined, needed: WorkspaceRole): string | null {
  if (canIn(workspace, needed))
    return null
  if (workspace?.archived && needed !== 'viewer')
    return 'This workspace is archived: it is read-only'
  return needed === 'owner' ? 'Only owners can do this' : 'Only editors and owners can do this'
}
