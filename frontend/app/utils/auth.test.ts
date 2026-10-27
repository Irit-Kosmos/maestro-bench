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

import { describe, expect, it } from 'vitest'
import { loginErrorMessage, safeNextPath } from './auth'

describe('safeNextPath', () => {
  it('keeps a path of the app, with its query', () => {
    expect(safeNextPath('/experiments/3?tab=runs')).toBe('/experiments/3?tab=runs')
  })

  it.each(['https://evil.example', '//evil.example', '/\\evil.example', 'evil', '', undefined, 3])(
    'falls back to the dashboard for %s',
    (value) => {
      expect(safeNextPath(value)).toBe('/')
    },
  )
})

describe('loginErrorMessage', () => {
  it('explains the errors the backend reports', () => {
    expect(loginErrorMessage('not_allowed')).toContain('isn’t allowed')
    expect(loginErrorMessage('inactive')).toContain('deactivated')
    expect(loginErrorMessage('session_expired')).toContain('expired')
  })

  it('has a generic message for an unknown code', () => {
    expect(loginErrorMessage('whatever')).toBe(loginErrorMessage('login_failed'))
  })

  it('says nothing when there is no error', () => {
    expect(loginErrorMessage(undefined)).toBeNull()
    expect(loginErrorMessage('')).toBeNull()
  })
})
