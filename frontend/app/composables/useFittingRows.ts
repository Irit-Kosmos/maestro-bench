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

import type { MaybeRefOrGetter } from 'vue'
import { useElementSize, useMediaQuery } from '@vueuse/core'

/**
 * How many rows of a list fit in a box, for the blocks that fill the dashboard's height without
 * scrolling. `offset` is what the block takes besides its rows (its header, its borders), and
 * `rowHeight` counts the divider under each row, which the last one does not have. The box is
 * measured, not the block: the block then stays as tall as what it shows. Below `xl` the page
 * stacks and scrolls, so the list keeps `fallback` rows.
 */
export function useFittingRows(box: MaybeRefOrGetter<HTMLElement | null | undefined>, rowHeight: number, fallback: number, offset = 0) {
  const { height } = useElementSize(box)
  const filling = useMediaQuery('(min-width: 1280px)')

  return computed(() => {
    if (!filling.value || !height.value)
      return fallback
    return Math.max(1, Math.floor((height.value - offset + 1) / rowHeight))
  })
}
