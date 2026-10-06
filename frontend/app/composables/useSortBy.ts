import type { SortState } from '~/utils/sorts'
import { useLocalStorage } from '@vueuse/core'
import { decodeSort, encodeSort } from '~/utils/sorts'

/**
 * How a list is sorted, remembered per browser. "No sorting" is null, which local storage can't keep (see `useGroupBy`),
 * so the choice is stored as one word.
 */
export function useSortBy(key: string, fallback: SortState | null = null) {
  const stored = useLocalStorage<string>(workspaceStorageKey(key), encodeSort(fallback))
  return computed<SortState | null>({
    get: () => decodeSort(stored.value),
    set: (value) => {
      stored.value = encodeSort(value)
    },
  })
}
