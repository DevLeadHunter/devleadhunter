import type { DemoSiteServiceCard, DemoSiteTheme } from '~/services/demoSiteService'
import type { TemplatePreviewDevice } from '~/types/TemplatePicker'

/** Props of the atelier preview: the published site, redrawn live with the unsaved edits. */
export type AtelierPreviewProps = {
  siteUrl: string
  device?: TemplatePreviewDevice
  templateId: string
  previewTheme?: DemoSiteTheme | null
  previewPhotos?: string[] | null
  previewServices?: DemoSiteServiceCard[] | null
  reloadNonce?: number
}

/** The size of a real screen, in CSS pixels at scale 1. */
export type AtelierPreviewScreenSize = {
  width: number
  height: number
}
