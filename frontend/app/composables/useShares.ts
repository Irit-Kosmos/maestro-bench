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

import type { Share, ShareKind } from '~/types'

/** The public links of a workspace's items: who may read an item without an account. */
export function useShares() {
  const { $api } = useNuxtApp()

  /** The active link of an item, or null when it is not shared */
  function getShare(kind: ShareKind, itemId: number) {
    return $api<Share | null>('/shares', { query: { kind, item_id: itemId } })
  }

  /** The link of an item: the active one when there is one, else a new one */
  function createShare(kind: ShareKind, itemId: number) {
    return $api<Share>('/shares', { method: 'POST', body: { kind, item_id: itemId } })
  }

  /** Withdraw a link: it stops answering at once */
  function revokeShare(id: number) {
    return $api(`/shares/${id}`, { method: 'DELETE' })
  }

  /** The address to give out */
  function linkOf(share: Share): string {
    return `${window.location.origin}${inShare(share.token, '/')}`
  }

  return { getShare, createShare, revokeShare, linkOf }
}
