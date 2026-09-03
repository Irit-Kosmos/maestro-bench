export const useMyLazyFetch: typeof useLazyFetch = (request, opts?) => {
  const runtimeConfig = useRuntimeConfig()
  return useLazyFetch(request, {
    baseURL: runtimeConfig.public.BACK_URL,
    ...opts,
  })
}
