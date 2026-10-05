/** The workspace of the current URL (`/w/<slug>/...`) and the path inside it. */
export function useWorkspace() {
  const route = useRoute()
  const slug = computed(() => workspaceOfPath(route.path))
  const relativePath = computed(() => stripWorkspace(route.path))

  return { slug, relativePath }
}

/**
 * A localStorage key that belongs to the current workspace: `maestro:models-group-by` becomes
 * `maestro:<slug>:models-group-by`, so what you set up in one workspace does not follow you into another.
 * Switching workspace reloads the page, so the slug read here is the one for the whole page.
 */
export function workspaceStorageKey(key: string): string {
  const slug = workspaceOfPath(useRoute().path)
  return slug ? key.replace(/^maestro:/, `maestro:${slug}:`) : key
}
