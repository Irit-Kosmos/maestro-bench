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

import type { ProviderStatus } from '~/types'

/**
 * Which providers the workspace can call, by canonical provider key, to warn before a run
 * that would fail for want of an API key.
 */
export function useProviderStatus() {
  const { data } = useMyLazyFetch<ProviderStatus[]>('/providers')
  const { isOwner } = useCurrentWorkspace()

  const byKey = computed<Readonly<Record<string, ProviderStatus>>>(() => Object.fromEntries(
    (data.value ?? []).map(item => [providerMeta(item.provider).key, item]),
  ))

  /** Known, and with neither a workspace key nor an instance key (a URL provider is "configured" once its URL is set) */
  function lacksCredentials(provider: string | null | undefined) {
    const status = provider ? byKey.value[providerMeta(provider).key] : undefined
    return !!status && !status.configured
  }

  /** What to do about it: owners can add the key themselves */
  const missingKeyAdvice = computed(() => isOwner.value ? 'Add one in Settings.' : 'Ask an owner to add one.')

  return { byKey, lacksCredentials, missingKeyAdvice }
}
