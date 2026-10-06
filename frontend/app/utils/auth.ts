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
