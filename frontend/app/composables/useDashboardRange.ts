import type { DashboardRange } from '~/types'
import { useLocalStorage } from '@vueuse/core'
import { isDashboardRange } from '~/utils/dashboard'

/**
 * The period the dashboard covers. The URL wins, so a view can be shared; otherwise the last
 * one picked, which is remembered across visits.
 */
export function useDashboardRange() {
  const route = useRoute()
  const router = useRouter()
  const remembered = useLocalStorage<DashboardRange>('maestro:dashboard-range', '7d')

  return computed<DashboardRange>({
    get() {
      const fromUrl = route.query.range
      if (isDashboardRange(fromUrl))
        return fromUrl
      return isDashboardRange(remembered.value) ? remembered.value : '7d'
    },
    set(value) {
      remembered.value = value
      router.replace({ query: { ...route.query, range: value } })
    },
  })
}
