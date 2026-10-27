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

export type FetchErrorKind = 'error' | 'not-found' | 'forbidden' | 'gone'

/** What a failed request means for the person looking at the page */
export function fetchErrorKind(error: unknown): FetchErrorKind {
  const status = error as { statusCode?: number, status?: number } | null | undefined
  const code = status?.statusCode ?? status?.status
  if (code === 404)
    return 'not-found'
  if (code === 403)
    return 'forbidden'
  // A public link its author withdrew
  if (code === 410)
    return 'gone'
  return 'error'
}
