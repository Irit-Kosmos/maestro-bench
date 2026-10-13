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

/**
 * The pages a public link opens, by the first segment of their path. Each one is a page of the app, served
 * again under `/s/<token>/...` (see `sharedRoutePath`) with its requests sent to the link instead of to a
 * workspace.
 */
export const SHARED_RESOURCES = ['experiments', 'batches', 'analyses', 'studies']

/** The token in a `/s/<token>/...` path, if there is one. */
export function shareOfPath(path: string): string | null {
  return /^\/s\/([^/?#]+)/.exec(path)?.[1] ?? null
}

/** `/experiments/3` behind a link → `/s/<token>/experiments/3`. */
export function inShare(token: string, path: string): string {
  return `/s/${token}${path === '/' ? '' : path}`
}

/** Whether a path without a workspace or a link is a page that a link can open: `/experiments/3`. */
export function isSharedPagePath(path: string): boolean {
  return SHARED_RESOURCES.some(resource => new RegExp(`^/${resource}/\\d+(?:[/?#]|$)`).test(path))
}

/**
 * `/w/:slug()/experiments/:id()` → `/s/:token()/experiments/:id()`: the route path of a workspace page that a
 * link opens, behind the link. Null for any other route.
 */
export function sharedRoutePath(routePath: string): string | null {
  const rest = unscopedRoutePath(routePath)
  if (!rest || !SHARED_RESOURCES.some(resource => rest === `/${resource}/:id()`))
    return null
  return `/s/:token()${rest}`
}

/**
 * Where a request of the app really goes. The app says `/experiments/3`; behind a link that is the link's own
 * API (`/shared/<token>/experiments/3`, `/shared/<token>` for the link itself), inside a workspace it is the
 * workspace's. Null when the page is neither.
 */
export function scopeApiPath(request: string, pagePath: string): string | null {
  const token = shareOfPath(pagePath)
  if (token)
    return `/shared/${token}${request === '/' ? '' : request}`
  const slug = workspaceOfPath(pagePath)
  return slug ? `/workspaces/${slug}${request}` : null
}
