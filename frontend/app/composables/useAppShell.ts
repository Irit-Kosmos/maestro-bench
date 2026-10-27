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
  // Keyed inside the workspace, like the breadcrumb that reads it
  const path = stripWorkspace(route.path)

  watch(() => toValue(label), (value) => {
    if (value)
      labels.value = { ...labels.value, [path]: value }
  }, { immediate: true })
}
