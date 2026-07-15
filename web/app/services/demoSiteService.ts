import { api } from '~/services/api'

const BASE_URL = '/api/v1/demo-sites'

export interface DemoSiteTheme {
  primary: string
  secondary: string
  accent: string
}

export interface DemoSiteTemplate {
  id: string
  name: string
  description: string
  preview_image_url?: string | null
  default_theme: DemoSiteTheme
  category?: string
}

export interface DemoSiteCreatePayload {
  business_name: string
  template_id: string
  email: string
  invite_client_to_cms?: boolean
  phone?: string
  city?: string
  description?: string
  theme?: DemoSiteTheme
  prospect_id?: number
}

export interface DemoSitePreviewPayload {
  business_name: string
  template_id: string
  phone?: string
  email?: string
  city?: string
  description?: string
  theme?: DemoSiteTheme
}

export interface DemoSitePreviewResult {
  template_id: string
  content_json: Record<string, unknown>
}

export interface DemoSiteUpdatePayload {
  business_name?: string
  template_id?: string
  email?: string
  phone?: string
  city?: string
  description?: string
  theme?: DemoSiteTheme
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
  theme?: DemoSiteTheme | null
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
 * Build preview content without provisioning Storyblok/Vercel.
 */
export async function previewDemoSite(payload: DemoSitePreviewPayload): Promise<DemoSitePreviewResult> {
  return api.post<DemoSitePreviewResult>(`${BASE_URL}/preview`, payload)
}

/**
 * List demo sites created by the current user.
 */
export async function listDemoSites(): Promise<DemoSiteListResponse> {
  return api.get<DemoSiteListResponse>(BASE_URL)
}

/**
 * Create and provision a demo website.
 */
export async function createDemoSite(payload: DemoSiteCreatePayload): Promise<DemoSite> {
  return api.post<DemoSite>(BASE_URL, payload)
}

/** Payload to generate demo sites for several prospects with one template. */
export interface BulkGeneratePayload {
  prospect_ids: number[]
  template_id: string
  theme?: DemoSiteTheme
  invite_client_to_cms?: boolean
}

/** Per-prospect outcome of a bulk site generation. */
export interface BulkGenerateItemResult {
  prospect_id: number
  demo_site_id?: number
  slug?: string
  status: string
  error?: string
}

/** Aggregated result of a bulk site generation. */
export interface BulkGenerateResult {
  results: BulkGenerateItemResult[]
  created: number
  failed: number
  skipped_no_email: Array<{ id: number; name: string }>
  total: number
}

/**
 * Generate demo sites for several prospects using the same template.
 * Prospects without an email are reported in ``skipped_no_email``.
 */
export async function createDemoSitesBulk(payload: BulkGeneratePayload): Promise<BulkGenerateResult> {
  return api.post<BulkGenerateResult>(`${BASE_URL}/bulk`, payload)
}

/**
 * Fetch a single demo site by id.
 */
export async function getDemoSite(demoSiteId: number): Promise<DemoSite> {
  return api.get<DemoSite>(`${BASE_URL}/${demoSiteId}`)
}

/**
 * Re-run live URL verification for a demo site.
 */
export async function verifyDemoSite(demoSiteId: number): Promise<DemoSite> {
  return api.post<DemoSite>(`${BASE_URL}/${demoSiteId}/verify`, {})
}

/**
 * Update demo site fields and regenerate its content.
 */
export async function updateDemoSite(demoSiteId: number, payload: DemoSiteUpdatePayload): Promise<DemoSite> {
  return api.patch<DemoSite>(`${BASE_URL}/${demoSiteId}`, payload)
}

/**
 * Rebuild demo site content from stored fields without changing them.
 */
export async function regenerateDemoSite(demoSiteId: number): Promise<DemoSite> {
  return api.post<DemoSite>(`${BASE_URL}/${demoSiteId}/regenerate`, {})
}

/**
 * Send a Storyblok CMS invitation to the demo site client.
 */
export async function inviteDemoSiteClientToCms(demoSiteId: number): Promise<DemoSite> {
  return api.post<DemoSite>(`${BASE_URL}/${demoSiteId}/invite-cms`, {})
}

/**
 * Delete a demo site owned by the current user.
 */
export async function deleteDemoSite(demoSiteId: number): Promise<void> {
  await api.delete(`${BASE_URL}/${demoSiteId}`)
}

/**
 * Download the generated site's source code as a standalone, runnable zip.
 *
 * Streams the authenticated binary response as a Blob and triggers a browser
 * download (the shared ``api`` client only handles JSON, so this fetches directly).
 * @param demoSiteId - Id of the demo site to export.
 * @param slug - Site slug, used to name the downloaded file.
 * @throws {Error} When the export request fails (message from the API when available).
 */
export async function exportDemoSiteCode(demoSiteId: number, slug: string): Promise<void> {
  const userStore = useUserStore()
  const config = useRuntimeConfig()
  const response = await fetch(`${config.public.apiBase}${BASE_URL}/${demoSiteId}/export`, {
    headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    let errorMessage = `Export échoué : ${response.statusText}`
    if (errorText) {
      try {
        errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
      } catch {
        errorMessage = errorText
      }
    }
    throw new Error(errorMessage)
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${slug}-site.zip`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

/**
 * Compute days remaining before a demo site expires.
 */
export function daysUntilExpiry(expiresAt: string): number {
  const diff = new Date(expiresAt).getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
}

/**
 * Best URL to open/share for a demo site (prefers live local URL in dev).
 */
export function getDemoSiteOpenUrl(site: DemoSite): string | null {
  if (site.demo_url_live && site.demo_url) {
    return site.demo_url
  }
  if (site.local_demo_url) {
    return site.local_demo_url
  }
  return site.demo_url ?? null
}

/**
 * Whether the demo site is reachable (prod URL or local fallback).
 */
export function isDemoSiteReachable(site: DemoSite): boolean {
  return Boolean(site.demo_url_live || site.local_demo_url)
}
