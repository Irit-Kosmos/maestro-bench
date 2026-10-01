import type { MaybeRefOrGetter } from 'vue'

/** Open state of the keyboard shortcuts overlay, shared by the layout and the sidebar. */
export function useShortcutsOverlay() {
  return useState('shortcuts-open', () => false)
}

/** Breadcrumb labels keyed by route path, so `/experiments/12` can read as the experiment name. */
export function useBreadcrumbLabels() {
  return useState<Record<string, string>>('breadcrumb-labels', () => ({}))
}

/** Name the current route's last breadcrumb (e.g. with the entity name once it has loaded). */
export function useBreadcrumbLabel(label: MaybeRefOrGetter<string | null | undefined>) {
  const route = useRoute()
  const labels = useBreadcrumbLabels()
  const path = route.path

  watch(() => toValue(label), (value) => {
    if (value)
      labels.value = { ...labels.value, [path]: value }
  }, { immediate: true })
}
