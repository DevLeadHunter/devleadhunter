import type { SiteLegalNotice } from '~/types/SiteLegalNotice'

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
  owner_profile_photo_url?: string | null
  owner_contact_phone?: string | null
  owner_contact_email?: string | null
  sale_price_label?: string | null
  expiry_date_label?: string | null
  business_category?: string | null
  business_photo_url?: string | null
  legal?: SiteLegalNotice | null
}

/** Public payload of a demo taken offline at its deadline, for the page its old link shows. */
export type DemoSiteWithdrawn = {
  slug: string
  business_name: string
  withdrawn_on_label: string | null
  revived_until_label: string
  sale_price_label: string | null
  owner_name: string | null
  owner_company_name: string | null
  owner_company_website_url: string | null
  owner_profile_photo_url: string | null
  owner_contact_phone: string | null
  owner_contact_email: string | null
}
