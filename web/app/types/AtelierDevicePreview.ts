import type { TemplatePreviewDevice } from '~/types/TemplatePicker'

/** Props of the device preview: a published page in a real screen, told the unsaved edits through `dlh:preview`. */
export type AtelierDevicePreviewProps = {
  pageUrl: string
  device?: TemplatePreviewDevice
  previewMessage?: Record<string, unknown> | null
  reloadNonce?: number
}
