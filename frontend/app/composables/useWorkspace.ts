/** The workspace of the current URL (`/w/<slug>/...`) and the path inside it. */
export function useWorkspace() {
  const route = useRoute()
  const slug = computed(() => workspaceOfPath(route.path))
  const relativePath = computed(() => stripWorkspace(route.path))

  return { slug, relativePath }
}
