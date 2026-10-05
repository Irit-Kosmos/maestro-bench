import type { Workspace } from '~/types'

const LAST_WORKSPACE_KEY = 'maestro-workspace'

/**
 * The workspaces the signed-in user belongs to.
 *
 * Everything the app shows lives in one workspace at a time, named by the URL.
 * Changing workspace reloads the page, so nothing of the other one stays in memory.
 */
export function useWorkspaces() {
  const workspaces = useState<Workspace[] | null>('workspaces', () => null)
  const backUrl = useRuntimeConfig().public.BACK_URL as string

  async function load(): Promise<Workspace[]> {
    workspaces.value = await $fetch<Workspace[]>(`${backUrl}/workspaces`, { credentials: 'include' })
    return workspaces.value
  }

  /** The workspace to open when the URL names none: the one used last, else the first. */
  function defaultSlug(preferred?: string | null): string | null {
    const known = workspaces.value ?? []
    for (const candidate of [preferred, lastUsedSlug()]) {
      if (candidate && known.some(w => w.slug === candidate))
        return candidate
    }
    return known[0]?.slug ?? null
  }

  function lastUsedSlug(): string | null {
    try {
      return localStorage.getItem(LAST_WORKSPACE_KEY)
    }
    catch {
      return null
    }
  }

  function remember(slug: string) {
    try {
      localStorage.setItem(LAST_WORKSPACE_KEY, slug)
    }
    catch {
      // Private mode: the first workspace is the fallback
    }
  }

  /** Open a workspace (a full reload, on purpose) */
  function open(slug: string) {
    return navigateTo(inWorkspace(slug, '/'), { external: true })
  }

  async function create(name: string): Promise<Workspace> {
    const created = await useNuxtApp().$api<Workspace>('/workspaces', { method: 'POST', body: { name } })
    workspaces.value = [...(workspaces.value ?? []), created]
    return created
  }

  return { workspaces, load, defaultSlug, remember, open, create }
}
