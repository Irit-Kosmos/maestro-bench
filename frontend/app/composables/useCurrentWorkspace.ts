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

import type { WorkspaceRole } from '~/types'

/** The workspace of the current URL, with what the signed-in user may do in it. */
export function useCurrentWorkspace() {
  const { slug } = useWorkspace()
  const { workspaces } = useWorkspaces()

  const workspace = computed(() => workspaces.value?.find(w => w.slug === slug.value) ?? null)
  const role = computed(() => workspace.value?.role ?? null)
  const archived = computed(() => workspace.value?.archived ?? false)

  /** Whether the user's role is at least `needed`; always false in an archived workspace, which is read-only */
  const can = (needed: WorkspaceRole): boolean => canIn(workspace.value, needed)

  /** Why `needed` is out of reach, for a tooltip; null when it is not */
  const denial = (needed: WorkspaceRole): string | null => denialReason(workspace.value, needed)

  return {
    workspace,
    role,
    archived,
    isOwner: computed(() => role.value === 'owner'),
    /** Create, edit, delete and run things: editors and owners, in a workspace that is not archived */
    canEdit: computed(() => can('editor')),
    can,
    denial,
  }
}
