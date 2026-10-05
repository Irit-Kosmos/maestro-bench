import { describe, expect, it } from 'vitest'
import { canIn, denialReason } from './roles'

const as = (role: 'viewer' | 'editor' | 'owner', archived = false) => ({ role, archived })

describe('canIn', () => {
  it.each([
    ['viewer', 'viewer', true],
    ['viewer', 'editor', false],
    ['viewer', 'owner', false],
    ['editor', 'viewer', true],
    ['editor', 'editor', true],
    ['editor', 'owner', false],
    ['owner', 'viewer', true],
    ['owner', 'editor', true],
    ['owner', 'owner', true],
  ] as const)('a %s needing %s: %s', (role, needed, expected) => {
    expect(canIn(as(role), needed)).toBe(expected)
  })

  it('leaves only reading in an archived workspace, whatever the role', () => {
    expect(canIn(as('owner', true), 'viewer')).toBe(true)
    expect(canIn(as('owner', true), 'editor')).toBe(false)
    expect(canIn(as('owner', true), 'owner')).toBe(false)
  })

  it('allows nothing outside a workspace', () => {
    expect(canIn(null, 'viewer')).toBe(false)
    expect(canIn(undefined, 'viewer')).toBe(false)
  })
})

describe('denialReason', () => {
  it('says nothing when the action is allowed', () => {
    expect(denialReason(as('editor'), 'editor')).toBeNull()
  })

  it('names who may do it', () => {
    expect(denialReason(as('viewer'), 'editor')).toBe('Only editors and owners can do this')
    expect(denialReason(as('editor'), 'owner')).toBe('Only owners can do this')
  })

  it('blames the archive before the role', () => {
    expect(denialReason(as('viewer', true), 'editor')).toContain('archived')
    expect(denialReason(as('owner', true), 'owner')).toContain('archived')
  })
})
