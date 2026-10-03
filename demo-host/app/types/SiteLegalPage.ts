import type { SiteLegalNotice } from '~/types/SiteLegalNotice'

/** `siteHref` leads back to the site and keeps a demo's query. */
export type SiteLegalPageProps = {
  legalNotice: SiteLegalNotice
  businessName: string
  siteHref: string
}
