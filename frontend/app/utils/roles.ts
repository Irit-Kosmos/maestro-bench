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
