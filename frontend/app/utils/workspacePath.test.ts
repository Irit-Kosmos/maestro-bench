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
import { inShare, inWorkspace, isSharedPagePath, isWorkspaceApiPath, scopeApiPath, sharedRoutePath, shareOfPath, stripWorkspace, unscopedRoutePath, workspaceOfPath } from './workspacePath'

describe('stripWorkspace', () => {
  it('keeps the part inside the workspace', () => {
    expect(stripWorkspace('/w/team-a/experiments/3')).toBe('/experiments/3')
    expect(stripWorkspace('/w/team-a')).toBe('/')
  })

  it('leaves other paths alone', () => {
    expect(stripWorkspace('/login')).toBe('/login')
    expect(stripWorkspace('/')).toBe('/')
  })
})

describe('workspaceOfPath', () => {
  it('reads the slug', () => {
    expect(workspaceOfPath('/w/team-a/models')).toBe('team-a')
    expect(workspaceOfPath('/w/team-a')).toBe('team-a')
  })

  it('finds none outside a workspace', () => {
    expect(workspaceOfPath('/w')).toBeNull()
    expect(workspaceOfPath('/experiments')).toBeNull()
    expect(workspaceOfPath('/wow/x')).toBeNull()
  })
})

describe('inWorkspace', () => {
  it('prefixes a path', () => {
    expect(inWorkspace('a', '/experiments/3')).toBe('/w/a/experiments/3')
  })

  it('maps the dashboard to the workspace itself', () => {
    expect(inWorkspace('a', '/')).toBe('/w/a')
  })
})

describe('unscopedRoutePath', () => {
  it('drops the workspace from a route path', () => {
    expect(unscopedRoutePath('/w/:slug()/experiments/new')).toBe('/experiments/new')
    expect(unscopedRoutePath('/w/:slug()/experiments/:id()')).toBe('/experiments/:id()')
    expect(unscopedRoutePath('/w/:slug/models')).toBe('/models')
  })

  it('maps the dashboard to the root', () => {
    expect(unscopedRoutePath('/w/:slug()')).toBe('/')
    expect(unscopedRoutePath('/w/:slug()/')).toBe('/')
  })

  it('finds none outside a workspace', () => {
    expect(unscopedRoutePath('/w')).toBeNull()
    expect(unscopedRoutePath('/login')).toBeNull()
    expect(unscopedRoutePath('/join/:token()')).toBeNull()
  })
})

describe('isWorkspaceApiPath', () => {
  it.each(['/experiments', '/experiments/3?x=1', '/providers', '/events', '/dashboard?range=7d'])(
    '%s lives in a workspace',
    (path) => {
      expect(isWorkspaceApiPath(path)).toBe(true)
    },
  )

  it.each(['/auth/me', '/auth/logout', '/workspaces', '/workspaces/a/tags', '/workspaces?x=1', '/invitations/abc', '/health'])(
    '%s does not',
    (path) => {
      expect(isWorkspaceApiPath(path)).toBe(false)
    },
  )

  it('does not mistake a longer name for an unscoped one', () => {
    expect(isWorkspaceApiPath('/authors')).toBe(true)
    expect(isWorkspaceApiPath('/workspaces-x')).toBe(true)
  })

  it('leaves full URLs alone', () => {
    expect(isWorkspaceApiPath('https://example.org/x')).toBe(false)
  })
})

describe('shareOfPath', () => {
  it('reads the token', () => {
    expect(shareOfPath('/s/k7Xq2mPz/experiments/3')).toBe('k7Xq2mPz')
    expect(shareOfPath('/s/k7Xq2mPz')).toBe('k7Xq2mPz')
    expect(shareOfPath('/s/a-b_c?x=1')).toBe('a-b_c')
  })

  it('finds none elsewhere', () => {
    expect(shareOfPath('/s')).toBeNull()
    expect(shareOfPath('/w/team/experiments/3')).toBeNull()
    expect(shareOfPath('/settings/x')).toBeNull()
  })
})

describe('inShare', () => {
  it('prefixes a path', () => {
    expect(inShare('abc', '/experiments/3')).toBe('/s/abc/experiments/3')
    expect(inShare('abc', '/')).toBe('/s/abc')
  })
})

describe('isSharedPagePath', () => {
  it('knows the pages a link opens', () => {
    expect(isSharedPagePath('/experiments/3')).toBe(true)
    expect(isSharedPagePath('/experiments/3?x=1')).toBe(true)
    expect(isSharedPagePath('/batches/3')).toBe(true)
    expect(isSharedPagePath('/analyses/3')).toBe(true)
    expect(isSharedPagePath('/studies/3?tab=items')).toBe(true)
  })

  it('leaves everything else to the app', () => {
    expect(isSharedPagePath('/experiments')).toBe(false)
    expect(isSharedPagePath('/experiments/new')).toBe(false)
    expect(isSharedPagePath('/analyses/new')).toBe(false)
    expect(isSharedPagePath('/datasets/3')).toBe(false)
    expect(isSharedPagePath('/models')).toBe(false)
    expect(isSharedPagePath('/')).toBe(false)
    expect(isSharedPagePath('/login')).toBe(false)
  })
})

describe('sharedRoutePath', () => {
  it('moves a page of a workspace behind a link', () => {
    expect(sharedRoutePath('/w/:slug()/experiments/:id()')).toBe('/s/:token()/experiments/:id()')
    expect(sharedRoutePath('/w/:slug()/studies/:id()')).toBe('/s/:token()/studies/:id()')
  })

  it('leaves out the pages a link does not open', () => {
    expect(sharedRoutePath('/w/:slug()/experiments/new')).toBeNull()
    expect(sharedRoutePath('/w/:slug()/experiments')).toBeNull()
    expect(sharedRoutePath('/w/:slug()/models')).toBeNull()
    expect(sharedRoutePath('/experiments/:id()')).toBeNull()
  })
})

describe('scopeApiPath', () => {
  it('sends a workspace page to its workspace', () => {
    expect(scopeApiPath('/experiments/3', '/w/team/experiments/3')).toBe('/workspaces/team/experiments/3')
  })

  it('sends a shared page to its link', () => {
    expect(scopeApiPath('/experiments/3', '/s/abc/experiments/3')).toBe('/shared/abc/experiments/3')
    expect(scopeApiPath('/', '/s/abc')).toBe('/shared/abc')
  })

  it('has nowhere to send a request of a page that is neither', () => {
    expect(scopeApiPath('/experiments/3', '/login')).toBeNull()
  })
})
