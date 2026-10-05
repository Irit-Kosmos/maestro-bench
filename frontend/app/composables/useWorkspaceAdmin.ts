import type {
  AcceptedInvitation,
  CreatedInvitation,
  InvitationPreview,
  ProviderStatus,
  Workspace,
  WorkspaceInvitation,
  WorkspaceMember,
  WorkspaceRole,
} from '~/types'

/**
 * Managing the current workspace: its members, invitations, API keys and life cycle.
 * These URLs name the workspace themselves, so the API plugin leaves them alone.
 */
export function useWorkspaceAdmin() {
  const { $api } = useNuxtApp()
  const { slug } = useWorkspace()
  const { workspaces } = useWorkspaces()
  const base = () => `/workspaces/${slug.value}`

  /** Keep the list of workspaces (the switcher, the role checks) in step with a change */
  function replaceWorkspace(updated: Workspace) {
    workspaces.value = (workspaces.value ?? []).map(w => w.slug === updated.slug ? updated : w)
  }

  const members = {
    list: () => $api<WorkspaceMember[]>(`${base()}/members`),
    add: (email: string, role: WorkspaceRole) =>
      $api<WorkspaceMember>(`${base()}/members`, { method: 'POST', body: { email, role } }),
    setRole: (userId: number, role: WorkspaceRole) =>
      $api<WorkspaceMember>(`${base()}/members/${userId}`, { method: 'PUT', body: { role } }),
    remove: (userId: number) => $api(`${base()}/members/${userId}`, { method: 'DELETE' }),
  }

  const invitations = {
    list: () => $api<WorkspaceInvitation[]>(`${base()}/invitations`),
    create: (role: WorkspaceRole) =>
      $api<CreatedInvitation>(`${base()}/invitations`, { method: 'POST', body: { role } }),
    revoke: (id: number) => $api(`${base()}/invitations/${id}`, { method: 'DELETE' }),
    /** The link to give to the invited person */
    link: (token: string) => `${window.location.origin}/join/${token}`,
  }

  const keys = {
    set: (provider: string, apiKey: string) =>
      $api<ProviderStatus>(`${base()}/providers/${provider}/key`, { method: 'PUT', body: { api_key: apiKey } }),
    remove: (provider: string) => $api(`${base()}/providers/${provider}/key`, { method: 'DELETE' }),
  }

  const lifecycle = {
    rename: async (name: string) => {
      const updated = await $api<Workspace>(base(), { method: 'PATCH', body: { name } })
      replaceWorkspace(updated)
      return updated
    },
    archive: async () => {
      const updated = await $api<Workspace>(`${base()}/archive`, { method: 'POST' })
      replaceWorkspace(updated)
      return updated
    },
    unarchive: async () => {
      const updated = await $api<Workspace>(`${base()}/unarchive`, { method: 'POST' })
      replaceWorkspace(updated)
      return updated
    },
    remove: (confirm: string) => $api(base(), { method: 'DELETE', query: { confirm } }),
  }

  return { members, invitations, keys, lifecycle }
}

/** Opening an invitation link: what it offers, then taking it */
export function useInvitation(token: string) {
  const { $api } = useNuxtApp()
  return {
    // The token goes in the body: URLs end up in the server's access logs
    preview: () => $api<InvitationPreview>('/invitations/preview', { method: 'POST', body: { token } }),
    accept: () => $api<AcceptedInvitation>('/invitations/accept', { method: 'POST', body: { token } }),
  }
}
