import type { SiteLegalNotice } from '~/types/SiteLegalNotice'

/** `legalPagePath` already carries the demo's query: each link appends its section anchor to it. */
export type SiteLegalFooterProps = {
  legalNotice: SiteLegalNotice
  legalPagePath: string
}
