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

import type { MaybeRefOrGetter, Ref } from 'vue'
import type { FilterSpec, FilterState } from '~/utils/filters'
import { buildFilterDefinitions, emptyFilterState, hasActiveFilters, matchesSpecs, matchesTerms, searchTerms } from '~/utils/filters'

/**
 * Search and filters of a list, in the shape `BaseListToolbar` expects.
 * The options of each filter are found in the items and counted, whatever the other filters say.
 * `searchText` returns everything about an item a search can match; every word must be found in it.
 * The state of the filters can be handed in, so the caller can seed it, persist it or read it.
 */
export function useListFilters<T>(
  source: MaybeRefOrGetter<readonly T[] | null | undefined>,
  specs: MaybeRefOrGetter<readonly FilterSpec<T>[]>,
  searchText: (item: T) => string,
  filters: Ref<FilterState> = ref({}),
) {
  const search = ref('')

  const items = computed(() => toValue(source) ?? [])
  const definitions = computed(() => buildFilterDefinitions(items.value, toValue(specs)))

  const filtered = computed(() => {
    const terms = searchTerms(search.value)
    const active = toValue(specs)
    return items.value.filter(item => matchesSpecs(item, active, filters.value) && matchesTerms(searchText(item), terms))
  })

  const hasFilters = computed(() => !!search.value.trim() || hasActiveFilters(filters.value))

  function clear() {
    search.value = ''
    filters.value = emptyFilterState(definitions.value)
  }

  return { search, filters, definitions, filtered, hasFilters, clear }
}
