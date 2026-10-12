/**
 * The public link the page is opened through (`/s/<token>/...`), if any.
 *
 * Behind a link the pages of the app are the same, read-only: no account, no workspace, and nothing that
 * is not in the link.
 */
export function useShare() {
  const route = useRoute()
  const token = computed(() => shareOfPath(route.path))

  return { token, isShared: computed(() => token.value !== null) }
}
