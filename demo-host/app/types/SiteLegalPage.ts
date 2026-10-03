import type { ComputedRef, Ref } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import type { SiteLegalNotice, SiteLegalPageKind } from '~/types/SiteLegalNotice'

/** Paths of a site's home and legal pages; on a demo they keep the visit's query. */
export type SiteLegalPagePaths = {
  home: string
  legal: string
  privacy: string
}

export type SiteLegalPageProps = {
  legalNotice: SiteLegalNotice
  page: SiteLegalPageKind
  businessName: string
  logoUrl: string | null
  pagePaths: SiteLegalPagePaths
}

export type SiteLegalPageData = {
  site: Ref<DemoSitePublic | undefined>
  isLoading: ComputedRef<boolean>
  hasFailed: ComputedRef<boolean>
  logoUrl: ComputedRef<string | null>
  pagePaths: ComputedRef<SiteLegalPagePaths>
}
