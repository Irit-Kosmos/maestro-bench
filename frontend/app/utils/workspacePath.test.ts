import { describe, expect, it } from 'vitest'
import { inWorkspace, isWorkspaceApiPath, stripWorkspace, workspaceOfPath } from './workspacePath'

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

describe('isWorkspaceApiPath', () => {
  it.each(['/experiments', '/experiments/3?x=1', '/providers', '/events', '/dashboard?range=7d'])(
    '%s lives in a workspace',
    (path) => {
      expect(isWorkspaceApiPath(path)).toBe(true)
    },
  )

  it.each(['/auth/me', '/auth/logout', '/workspaces', '/workspaces/a/tags', '/workspaces?x=1', '/health'])(
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
