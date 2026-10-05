import { useLocalStorage } from '@vueuse/core'

const NONE = 'none'

/**
 * How a list is grouped, remembered per browser. "No grouping" is null, which local storage can't keep: a null removes
 * the key, and a missing key reads as the default again. So it is stored as a word of its own.
 */
export function useGroupBy(key: string, fallback: string | null) {
  const stored = useLocalStorage<string>(key, fallback ?? NONE)
  return computed<string | null>({
    get: () => stored.value === NONE ? null : stored.value,
    set: (value) => {
      stored.value = value ?? NONE
    },
  })
}
