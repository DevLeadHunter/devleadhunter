import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/demo-sites'

export type DemoSiteTheme = {
  primary: string
  secondary: string
  accent: string
}

export type DemoSiteTemplate = {
  id: string
  name: string
  description: string
  preview_image_url?: string | null
  default_theme: DemoSiteTheme
  category?: string
}

export type DemoSiteCreatePayload = {
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

export type DemoSitePreviewPayload = {
  business_name: string
  template_id: string
  phone?: string
  email?: string
  city?: string
  description?: string
  theme?: DemoSiteTheme
}

export type DemoSitePreviewResult = {
  template_id: string
  content_json: Record<string, unknown>
}

export type DemoSiteUpdatePayload = {
  business_name?: string
  template_id?: string
  email?: string
  phone?: string
  city?: string
  description?: string
  theme?: DemoSiteTheme
}

export type DemoSite = {
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
  video_status?: DemoSiteVideoStatus | null
  video_error?: string | null
  video_generated_at?: string | null
  video_page_url?: string | null
  video_thumbnail_url?: string | null
}

/** Lifecycle of a demo site's prospection video (null = never generated). */
export type DemoSiteVideoStatus = 'pending' | 'generating' | 'ready' | 'failed'

export type DemoSiteListResponse = {
  items: DemoSite[]
  total: number
}

/** Payload to generate demo sites for several prospects with one template. */
export type BulkGeneratePayload = {
  prospect_ids: number[]
  template_id: string
  theme?: DemoSiteTheme
  invite_client_to_cms?: boolean
}

/** Per-prospect outcome of a bulk site generation. */
export type BulkGenerateItemResult = {
  prospect_id: number
  demo_site_id?: number
  slug?: string
  status: string
  error?: string
}

/** Aggregated result of a bulk site generation. */
export type BulkGenerateResult = {
  results: BulkGenerateItemResult[]
  created: number
  failed: number
  skipped_no_email: Array<{ id: number; name: string }>
  total: number
}

export class DemoSiteService {
  /**
   * Fetch templates available in the site builder stepper.
   */
  static async listDemoSiteTemplates(): Promise<DemoSiteTemplate[]> {
    return ApiClient.get<DemoSiteTemplate[]>(`${BASE_URL}/templates`)
  }

  /**
   * Build preview content without provisioning Storyblok/Vercel.
   */
  static async previewDemoSite(payload: DemoSitePreviewPayload): Promise<DemoSitePreviewResult> {
    return ApiClient.post<DemoSitePreviewResult>(`${BASE_URL}/preview`, payload)
  }

  /**
   * List demo sites created by the current user.
   */
  static async listDemoSites(): Promise<DemoSiteListResponse> {
    return ApiClient.get<DemoSiteListResponse>(BASE_URL)
  }

  /**
   * Create and provision a demo website.
   */
  static async createDemoSite(payload: DemoSiteCreatePayload): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(BASE_URL, payload)
  }

  /**
   * Generate demo sites for several prospects using the same template.
   * Prospects without an email are reported in ``skipped_no_email``.
   */
  static async createDemoSitesBulk(payload: BulkGeneratePayload): Promise<BulkGenerateResult> {
    return ApiClient.post<BulkGenerateResult>(`${BASE_URL}/bulk`, payload)
  }

  /**
   * Fetch a single demo site by id.
   */
  static async getDemoSite(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.get<DemoSite>(`${BASE_URL}/${demoSiteId}`)
  }

  /**
   * Re-run live URL verification for a demo site.
   */
  static async verifyDemoSite(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/verify`, {})
  }

  /**
   * Update demo site fields and regenerate its content.
   */
  static async updateDemoSite(demoSiteId: number, payload: DemoSiteUpdatePayload): Promise<DemoSite> {
    return ApiClient.patch<DemoSite>(`${BASE_URL}/${demoSiteId}`, payload)
  }

  /**
   * Rebuild demo site content from stored fields without changing them.
   */
  static async regenerateDemoSite(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/regenerate`, {})
  }

  /**
   * Send a Storyblok CMS invitation to the demo site client.
   */
  static async inviteDemoSiteClientToCms(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/invite-cms`, {})
  }

  /**
   * Delete a demo site owned by the current user.
   */
  static async deleteDemoSite(demoSiteId: number): Promise<void> {
    await ApiClient.delete(`${BASE_URL}/${demoSiteId}`)
  }

  /**
   * Start background generation of the prospection video (webcam + capture du site).
   * @param demoSiteId - Id of the demo site.
   * @returns The site with ``video_status`` set to ``pending``.
   */
  static async generateDemoSiteVideo(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/video`, {})
  }

  /**
   * Delete the generated prospection video and reset the site's video state.
   * @param demoSiteId - Id of the demo site.
   */
  static async deleteDemoSiteVideo(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.delete<DemoSite>(`${BASE_URL}/${demoSiteId}/video`)
  }

  /**
   * Download the generated site's source code as a standalone, runnable zip.
   *
   * Streams the authenticated binary response as a Blob and triggers a browser
   * download (the shared ``api`` client only handles JSON, so this fetches directly).
   * @param demoSiteId - Id of the demo site to export.
   * @param slug - Site slug, used to name the downloaded file.
   * @throws When the export request fails (message from the API when available).
   */
  static async exportDemoSiteCode(demoSiteId: number, slug: string): Promise<void> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}/${demoSiteId}/export`, {
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })

    if (!response.ok) {
      const errorText: string = await response.text().catch(() => '')
      let errorMessage: string = `Export échoué : ${response.statusText}`
      if (errorText) {
        try {
          errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
        } catch {
          errorMessage = errorText
        }
      }
      throw new Error(errorMessage)
    }

    const blob: Blob = await response.blob()
    const url: string = URL.createObjectURL(blob)
    const link: HTMLAnchorElement = document.createElement('a')
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
  static daysUntilExpiry(expiresAt: string): number {
    const diff: number = new Date(expiresAt).getTime() - Date.now()
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
  }

  /**
   * Best URL to open/share for a demo site (prefers live local URL in dev).
   */
  static getDemoSiteOpenUrl(site: DemoSite): string | null {
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
  static isDemoSiteReachable(site: DemoSite): boolean {
    return Boolean(site.demo_url_live || site.local_demo_url)
  }
}
