/**
 * Who you are, then where you are.
 *
 * Every page needs a signed-in user, except the login page and the pages behind a public link
 * (`/s/<token>/...`). Everything else lives in
 * a workspace (`/w/<slug>/...`): a path without one (`/experiments/3`, the way the
 * rest of the app links to pages) is sent to the workspace you were in.
 */
export default defineNuxtRouteMiddleware(async (to, from) => {
  // Behind a public link nobody signs in: the pages are the app's, read-only, in a layout of their own
  const token = shareOfPath(to.path)
  if (token) {
    setPageLayout('shared')
    return
  }
  // A page of the link that names another page the way the rest of the app does (`/experiments/3`)
  const fromToken = shareOfPath(from.path)
  if (fromToken && isSharedPagePath(to.path))
    return navigateTo(inShare(fromToken, to.fullPath))

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

    // A page that needs a role the user lacks (creating, in a workspace they can only read)
    const needed = to.meta.requiresRole
    const workspace = workspaces.value.find(w => w.slug === slug)
    if (needed && !canIn(workspace, needed)) {
      useToast().add({
        title: denialReason(workspace, needed) ?? 'Not allowed',
        color: 'warning',
        icon: 'i-ph-lock-bold',
      })
      return navigateTo(from.path !== to.path && workspaceOfPath(from.path) === slug ? from.fullPath : inWorkspace(slug, '/'))
    }
    return
  }

  // No `replace` here: a redirect inherits the method of the navigation it replaces, and forcing
  // `replace` would overwrite the page we come from in the history (Back would skip it)
  const target = defaultSlug(workspaceOfPath(from.path))
  if (!target)
    return navigateTo('/w')
  const rest = to.path === '/' ? to.fullPath.slice(1) : to.fullPath
  return navigateTo(`/w/${target}${rest}`)
})
