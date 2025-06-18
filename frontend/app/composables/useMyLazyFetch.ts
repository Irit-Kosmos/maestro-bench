const runtimeConfig = useRuntimeConfig()
export const useMyLazyFetch: typeof useLazyFetch = (request, opts?) => {
  return useLazyFetch(request, {
    baseURL: runtimeConfig.public.BACK_URL,
    ...opts,
  })
}
