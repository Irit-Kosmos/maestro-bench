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
