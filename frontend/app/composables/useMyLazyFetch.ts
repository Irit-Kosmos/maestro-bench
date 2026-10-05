export const useMyLazyFetch: typeof useLazyFetch = (request, opts?) => {
  // `$api` knows the backend's URL, sends the session cookie and the CSRF token
  return useLazyFetch(request, {
    $fetch: useNuxtApp().$api,
    ...opts,
  })
}
