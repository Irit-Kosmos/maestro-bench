/** `/w/<slug>/experiments/3` → `/experiments/3`: the part of a path that is inside a workspace. */
export function stripWorkspace(path: string): string {
  return path.replace(/^\/w\/[^/]+/, '') || '/'
}

/** The slug in a `/w/<slug>/...` path, if there is one. */
export function workspaceOfPath(path: string): string | null {
  return /^\/w\/([^/]+)/.exec(path)?.[1] ?? null
}

/** `/experiments/3` in a workspace → `/w/<slug>/experiments/3`; the dashboard is `/w/<slug>`. */
export function inWorkspace(slug: string, path: string): string {
  return `/w/${slug}${path === '/' ? '' : path}`
}

/** Paths the API serves outside any workspace. */
const UNSCOPED_API = ['/auth', '/workspaces', '/health']

export function isWorkspaceApiPath(request: string): boolean {
  if (!request.startsWith('/'))
    return false
  return !UNSCOPED_API.some(prefix =>
    request.startsWith(prefix) && /^(?:[/?#]|$)/.test(request.slice(prefix.length)),
  )
}
