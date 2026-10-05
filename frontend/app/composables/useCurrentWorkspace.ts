import type { WorkspaceRole } from '~/types'

const RANK: Record<WorkspaceRole, number> = { viewer: 0, editor: 1, owner: 2 }

/** The workspace of the current URL, with what the signed-in user may do in it. */
export function useCurrentWorkspace() {
  const { slug } = useWorkspace()
  const { workspaces } = useWorkspaces()

  const workspace = computed(() => workspaces.value?.find(w => w.slug === slug.value) ?? null)
  const role = computed(() => workspace.value?.role ?? null)
  const archived = computed(() => workspace.value?.archived ?? false)

  /** Whether the user's role is at least `needed`; always false in an archived workspace, which is read-only */
  function can(needed: WorkspaceRole): boolean {
    if (!role.value)
      return false
    return RANK[role.value] >= RANK[needed] && (needed === 'viewer' || !archived.value)
  }

  return { workspace, role, archived, isOwner: computed(() => role.value === 'owner'), can }
}
