import type { DemoSiteServiceCard, DemoSiteTheme } from '~/services/demoSiteService'
import type { TemplatePreviewDevice } from '~/types/TemplatePicker'

/** The tools of the atelier bar. */
export type DemoSiteAtelierToolKey = 'template' | 'couleurs' | 'photos' | 'prestations' | 'video' | 'plus'

/** One tool of the atelier bar and the title of its sheet. */
export type DemoSiteAtelierTool = {
  key: DemoSiteAtelierToolKey
  label: string
  icon: string
  title: string
  hint: string
}

/** One way of looking at the site in the atelier. */
export type DemoSitePreviewDeviceOption = {
  key: TemplatePreviewDevice
  label: string
  icon: string
}

/** Props of the atelier preview: the published site, redrawn live with the unsaved edits. */
export type DemoSiteAtelierPreviewProps = {
  siteUrl: string
  device?: TemplatePreviewDevice
  templateId: string
  previewTheme?: DemoSiteTheme | null
  previewPhotos?: string[] | null
  previewServices?: DemoSiteServiceCard[] | null
  reloadNonce?: number
}
