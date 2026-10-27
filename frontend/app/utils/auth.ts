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

/** A page of this app to come back to after signing in; anything else falls back to the dashboard. */
export function safeNextPath(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\'))
    return '/'
  return value
}

const LOGIN_ERRORS: Record<string, string> = {
  not_allowed: 'This account isn’t allowed to use this instance. Ask an administrator for access.',
  inactive: 'This account has been deactivated. Ask an administrator to reactivate it.',
  session_expired: 'Your session expired. Sign in to pick up where you left off.',
  login_failed: 'The sign-in didn’t complete. Try again.',
  unknown_provider: 'This sign-in method isn’t available.',
}

/** What to tell someone the backend sent back to the login page with `?error=` */
export function loginErrorMessage(code: unknown): string | null {
  if (typeof code !== 'string' || !code)
    return null
  return LOGIN_ERRORS[code] ?? LOGIN_ERRORS.login_failed!
}
