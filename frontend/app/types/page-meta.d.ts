import type { WorkspaceRole } from '~/types'

declare module '#app' {
  interface PageMeta {
    title?: string
    subtitle?: string
    /** The role a page needs; someone with a lower one is sent back to where they were */
    requiresRole?: WorkspaceRole
  }
}

export {}
