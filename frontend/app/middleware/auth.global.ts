/** Every page needs a signed-in user, except the login page, which sends signed-in users away. */
export default defineNuxtRouteMiddleware(async (to) => {
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
})
