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

/** How high the sheet stands: the setting height, with the site above it, or nearly the whole area. */
export type DemoSiteAtelierSheetSize = 'setting' | 'expanded'

/** A drag of the sheet's handle, followed from the finger or the pointer that started it. */
export type DemoSiteAtelierSheetDrag = {
  pointerId: number
  startY: number
  startHeight: number
  areaHeight: number
  hasMoved: boolean
}
