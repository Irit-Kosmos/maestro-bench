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
