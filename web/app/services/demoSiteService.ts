import { api } from '~/services/api'

const BASE_URL = '/api/v1/demo-sites'

export interface DemoSiteTemplate {
  id: string
  name: string
  description: string
  preview_image_url?: string | null
}

export interface DemoSiteCreatePayload {
  business_name: string
  template_id: string
  email: string
  phone?: string
  city?: string
  description?: string
}

export interface DemoSiteUpdatePayload {
  business_name?: string
  template_id?: string
  email?: string
  phone?: string
  city?: string
  description?: string
}

export interface DemoSite {
  id: number
  slug: string
  template_id: string
  business_name: string
  phone?: string | null
  email?: string | null
  city?: string | null
  description?: string | null
  status: string
  demo_url?: string | null
  demo_url_live?: boolean
  local_demo_url?: string | null
  verification_message?: string | null
  storyblok_editor_url?: string | null
  storyblok_login_email?: string | null
  storyblok_login_password?: string | null
  storyblok_invite_sent?: boolean
  expires_at: string
  created_at: string
  error_message?: string | null
}

export interface DemoSiteListResponse {
  items: DemoSite[]
  total: number
}

/**
 * Fetch templates available in the site builder stepper.
 */
export async function listDemoSiteTemplates(): Promise<DemoSiteTemplate[]> {
  return api.get<DemoSiteTemplate[]>(`${BASE_URL}/templates`)
}

/**
 * List demo sites created by the current user.
 */
export async function listDemoSites(): Promise<DemoSiteListResponse> {
  return api.get<DemoSiteListResponse>(BASE_URL)
}

/**
 * Create and provision a demo website.
 * @param payload - Business info and selected template.
 */
export async function createDemoSite(payload: DemoSiteCreatePayload): Promise<DemoSite> {
  return api.post<DemoSite>(BASE_URL, payload)
}

/**
 * Fetch a single demo site by id.
 * @param demoSiteId - Demo site primary key.
 */
export async function getDemoSite(demoSiteId: number): Promise<DemoSite> {
  return api.get<DemoSite>(`${BASE_URL}/${demoSiteId}`)
}

/**
 * Re-run live URL verification for a demo site.
 * @param demoSiteId - Demo site primary key.
 */
export async function verifyDemoSite(demoSiteId: number): Promise<DemoSite> {
  return api.post<DemoSite>(`${BASE_URL}/${demoSiteId}/verify`, {})
}

/**
 * Update demo site fields and regenerate its content.
 * @param demoSiteId - Demo site primary key.
 * @param payload - Partial business info to update.
 */
export async function updateDemoSite(demoSiteId: number, payload: DemoSiteUpdatePayload): Promise<DemoSite> {
  return api.patch<DemoSite>(`${BASE_URL}/${demoSiteId}`, payload)
}

/**
 * Rebuild demo site content from stored fields without changing them.
 * @param demoSiteId - Demo site primary key.
 */
export async function regenerateDemoSite(demoSiteId: number): Promise<DemoSite> {
  return api.post<DemoSite>(`${BASE_URL}/${demoSiteId}/regenerate`, {})
}
