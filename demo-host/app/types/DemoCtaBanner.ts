import type { DemoSitePublic } from '~/types/demoSite'

/** Props of the « Ce site vous plaît ? » lead banner shown on live demo and video pages. */
export type DemoCtaBannerProps = {
  site: DemoSitePublic
  isVideoPageVariant: boolean
}

/** Display states of the banner. */
export type DemoCtaBannerState = 'collapsed' | 'open' | 'sent'
