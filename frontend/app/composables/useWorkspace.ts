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
