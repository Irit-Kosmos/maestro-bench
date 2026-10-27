// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

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
  const remembered = useLocalStorage<DashboardRange>(workspaceStorageKey('maestro:dashboard-range'), '7d')

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
