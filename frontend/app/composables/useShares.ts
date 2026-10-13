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
