/**
 * Props for `DemoSitePreviewFrame` — a framed iframe of the demo-host renderer.
 * Either previews an existing published demo (by `slug`) or a template with
 * placeholder data (by `templateId`, before the demo is created).
 */
export type DemoSitePreviewFrameProps = {
  /** Template id, used for the placeholder preview when no `slug` is given. */
  templateId: string
  /** Business name shown over the placeholder template (builder preview). */
  businessName?: string
  /** Built content (kept for API compatibility; the iframe renders from demo-host). */
  content?: Record<string, unknown>
  /** Slug of an existing published demo → previews the real site instead of a placeholder. */
  slug?: string | null
  /** Iframe height in px. */
  height?: number
  /** Label shown in the fake browser chrome bar. */
  previewLabel?: string
}
