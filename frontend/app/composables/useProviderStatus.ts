import type { ProviderStatus } from '~/types'

/**
 * Which providers the workspace can call, by canonical provider key, to warn before a run
 * that would fail for want of an API key.
 */
export function useProviderStatus() {
  const { data } = useMyLazyFetch<ProviderStatus[]>('/providers')
  const { isOwner } = useCurrentWorkspace()

  const byKey = computed<Readonly<Record<string, ProviderStatus>>>(() => Object.fromEntries(
    (data.value ?? []).map(item => [providerMeta(item.provider).key, item]),
  ))

  /** Known, and with neither a workspace key nor an instance key (a URL provider is "configured" once its URL is set) */
  function lacksCredentials(provider: string | null | undefined) {
    const status = provider ? byKey.value[providerMeta(provider).key] : undefined
    return !!status && !status.configured
  }

  /** What to do about it: owners can add the key themselves */
  const missingKeyAdvice = computed(() => isOwner.value ? 'Add one in Settings.' : 'Ask an owner to add one.')

  return { byKey, lacksCredentials, missingKeyAdvice }
}
