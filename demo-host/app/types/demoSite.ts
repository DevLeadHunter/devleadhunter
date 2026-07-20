/** Public payload returned by the API for a demo / delivered site. */
export type DemoSitePublic = {
  slug: string
  business_name: string
  template_id: string
  storyblok_preview_token?: string | null
  storyblok_region?: string | null
  content_json?: Record<string, unknown> | null
  status: string
  /** True when a prospection video is generated (player page at /v/{slug}). */
  video_available?: boolean
  /** Public Cloudflare R2 URL of the generated mp4 (absent when no video). */
  video_url?: string | null
  /** Public Cloudflare R2 URL of the email thumbnail, used as the player poster. */
  video_thumbnail_url?: string | null
}
