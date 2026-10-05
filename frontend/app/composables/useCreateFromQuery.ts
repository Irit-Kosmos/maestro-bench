/**
 * Opens a page's "new …" dialog when it is reached with `?new=1`: the `C` shortcut and the
 * command palette lead there, and the address stays clean afterwards.
 */
export function useCreateFromQuery(open: () => void) {
  const route = useRoute()
  const router = useRouter()
  const { canEdit } = useCurrentWorkspace()

  async function check() {
    if (!route.query.new)
      return
    const { new: _new, ...query } = route.query
    await router.replace({ query })
    if (canEdit.value)
      open()
  }

  onMounted(check)
  watch(() => route.query.new, check)
}
