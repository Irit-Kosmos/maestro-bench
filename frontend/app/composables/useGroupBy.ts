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

import { useLocalStorage } from '@vueuse/core'

const NONE = 'none'

/**
 * How a list is grouped, remembered per browser. "No grouping" is null, which local storage can't keep: a null removes
 * the key, and a missing key reads as the default again. So it is stored as a word of its own.
 */
export function useGroupBy(key: string, fallback: string | null) {
  const stored = useLocalStorage<string>(workspaceStorageKey(key), fallback ?? NONE)
  return computed<string | null>({
    get: () => stored.value === NONE ? null : stored.value,
    set: (value) => {
      stored.value = value ?? NONE
    },
  })
}
