/**
 * Who you are, then where you are.
 *
 * Every page needs a signed-in user, except the login page. Everything else lives in
 * a workspace (`/w/<slug>/...`): a path without one (`/experiments/3`, the way the
 * rest of the app links to pages) is sent to the workspace you were in.
 */
export default defineNuxtRouteMiddleware(async (to, from) => {
  const { user, fetchMe } = useAuth()

  if (!user.value) {
    try {
      await fetchMe()
    }
    catch {
      // The API is unreachable: the login page says so instead of looping
      if (to.path !== '/login')
        return navigateTo('/login')
      return
    }
  }

  if (to.path === '/login')
    return user.value ? navigateTo(safeNextPath(to.query.next)) : undefined

  if (!user.value) {
    return navigateTo({
      path: '/login',
      query: to.fullPath === '/' ? {} : { next: to.fullPath },
    })
  }

  const { workspaces, load, defaultSlug, remember } = useWorkspaces()
  if (!workspaces.value)
    await load()

  // The page that lists your workspaces, and lets you create one; and the one that opens an invitation
  if (to.path === '/w' || to.path.startsWith('/join/'))
    return

  const slug = workspaceOfPath(to.path)
  if (slug) {
    if (!workspaces.value?.some(w => w.slug === slug))
      return navigateTo('/w')
    // Another workspace than the one on screen: reload, so nothing of the first stays in memory
    const current = workspaceOfPath(from.path)
    if (current && current !== slug)
      return navigateTo(to.fullPath, { external: true })
    remember(slug)
    return
  }

  const target = defaultSlug(workspaceOfPath(from.path))
  if (!target)
    return navigateTo('/w', { replace: true })
  const rest = to.path === '/' ? to.fullPath.slice(1) : to.fullPath
  return navigateTo(`/w/${target}${rest}`, { replace: true })
})
