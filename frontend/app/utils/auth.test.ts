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
