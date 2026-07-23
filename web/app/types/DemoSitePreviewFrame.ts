/**
 * Either previews an existing published demo (by `slug`) or a template with
 * placeholder data (by `templateId`, before the demo is created).
 */
export type DemoSitePreviewFrameProps = {
  templateId: string
  businessName?: string
  content?: Record<string, unknown>
  slug?: string | null
  height?: number
  previewLabel?: string
}
