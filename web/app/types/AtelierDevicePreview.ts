import type { TemplatePreviewDevice } from '~/types/TemplatePicker'

/** Props of the device preview: a published page in a real screen, told the unsaved edits through `dlh:preview`. */
export type AtelierDevicePreviewProps = {
  pageUrl: string
  device?: TemplatePreviewDevice
  previewMessage?: Record<string, unknown> | null
  reloadNonce?: number
}

/** The size of a real screen, in CSS pixels at scale 1. */
export type AtelierDevicePreviewScreenSize = {
  width: number
  height: number
}

/** One button of the atelier's device switch. */
export type AtelierDevicePreviewOption = {
  key: TemplatePreviewDevice
  label: string
  icon: string
}
