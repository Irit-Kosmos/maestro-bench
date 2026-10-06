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

/**
 * `/w/:slug()/experiments/:id()` → `/experiments/:id()`: the route path of a workspace page, without the
 * workspace. Null for a route that is not inside one.
 *
 * The app links to pages without the workspace (`/experiments/3`) and the auth middleware sends them to
 * `/w/<slug>/...`. Registered as routes of their own, these paths resolve, so the router does not warn
 * that it found no match for every link and shortcut.
 */
export function unscopedRoutePath(routePath: string): string | null {
  const match = /^\/w\/:slug(?:\(\))?(\/.*)?$/.exec(routePath)
  return match ? match[1] || '/' : null
}

/** Paths the API serves outside any workspace. */
const UNSCOPED_API = ['/auth', '/workspaces', '/invitations', '/health']

export function isWorkspaceApiPath(request: string): boolean {
  if (!request.startsWith('/'))
    return false
  return !UNSCOPED_API.some(prefix =>
    request.startsWith(prefix) && /^(?:[/?#]|$)/.test(request.slice(prefix.length)),
  )
}
