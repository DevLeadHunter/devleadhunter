/** Public payload returned by the API for a demo / delivered site. */
export type DemoSitePublic = {
  slug: string
  business_name: string
  template_id: string
  storyblok_preview_token?: string | null
  storyblok_region?: string | null
  content_json?: Record<string, unknown> | null
  status: string
  video_available?: boolean
  video_url?: string | null
  video_thumbnail_url?: string | null
  owner_name?: string | null
  owner_company_name?: string | null
  owner_company_website_url?: string | null
}
