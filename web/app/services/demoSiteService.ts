import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/demo-sites'

/** Context the desktop sidecar needs to render a site's video background. */
export type DemoSiteVideoBackgroundContext = {
  slug: string
  demo_url: string
  space_id: string
  story_id: string
  /** Trade-aware hero line typed in the editor demo (empty falls back to a neutral default). */
  accroche: string
  /** Resolved decision-maker first name for the greeting, or null. */
  first_name: string | null
  /** Presenter clip timing, so the desktop montage places the site/webcam segments. */
  presenter_duration: number
  presenter_intro: number
  presenter_outro: number
  site_seconds: number
  hold_seconds: number
  total_seconds: number
  out_width: number
  out_height: number
  fps: number
}

export type DemoSiteTheme = {
  primary: string
  secondary: string
  accent: string
}

/** Colors applied to a demo site that has no theme of its own yet. */
export const DEFAULT_DEMO_SITE_THEME: DemoSiteTheme = {
  primary: '#0284c7',
  secondary: '#0f172a',
  accent: '#f59e0b',
}

/** Canonical, template-agnostic colour roles the editor exposes. */
export type ColorRole = 'action' | 'fond' | 'secondaire'

export type DemoSiteTemplate = {
  id: string
  name: string
  description: string
  preview_image_url?: string | null
  default_theme: DemoSiteTheme
  category?: string
  trades?: string[]
  /** Role → palette key. Only listed roles are editable (a layer's dead colours are omitted). */
  color_roles?: Partial<Record<ColorRole, keyof DemoSiteTheme>>
  /** Palette key driving the action colour (== color_roles.action). */
  brand_color_key?: keyof DemoSiteTheme
  service_cards?: DemoSiteServiceCardsConfig | null
}

/** ``image`` is a photo URL of the site's pool, or '' (the site then falls back to a real gallery photo). */
export type DemoSiteServiceCard = {
  title: string
  description: string
  image: string
}

export type DemoSiteServiceCardsConfig = {
  enabled: boolean
  heading: string
  subject: string
  min_cards: number
  max_cards: number
  with_images: boolean
}

/** ``kind`` stays `unknown` until the photo is analysed; ``card_worthy`` = a dish or a drink. */
export type DemoSitePhotoLabel = {
  url: string
  kind: string
  description: string
  dishes: string[]
  appeal: number
  card_worthy: boolean
}

export type DemoSiteServiceCardsSource = 'manual' | 'ai' | 'ai_auto'

export type DemoSiteServiceCards = {
  cards: DemoSiteServiceCard[]
  override_active: boolean
  override_source: DemoSiteServiceCardsSource | null
  pool: DemoSitePhotoLabel[]
  ai_available: boolean
  labels_pending: number
  config: DemoSiteServiceCardsConfig
}

/** ``photo_index`` is the 1-based position of the card's photo in the pool, null without a photo. */
export type DemoSiteServiceCardSuggestion = DemoSiteServiceCard & {
  reason: string
  photo_index: number | null
}

export type DemoSiteServiceCardsAnalysis = {
  photos_total: number
  photos_labelled: number
  dish_photos: number
  menu_boards: number
  menu_dishes: number
  reviews_used: number
  model: string
}

export type DemoSiteServiceCardsSuggestionResult = {
  cards: DemoSiteServiceCardSuggestion[]
  pool: DemoSitePhotoLabel[]
  analysis: DemoSiteServiceCardsAnalysis
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
  /** Action colour from the prospect logo (true) or the template default (false). */
  use_brand_color?: boolean
  /** Curated photo placement ([0]→hero, [1]→about, [2:]→gallery), saved with the other edits in one regeneration. */
  image_order?: string[]
  /** Curated section cards; `[]` drops the curation (back to the generated cards). */
  services?: DemoSiteServiceCard[]
  services_source?: 'manual' | 'ai'
}

/** The site's photo pool and its current placement: order[0]→hero, order[1]→about, order[2:]→gallery. */
export type DemoSiteImages = {
  pool: string[]
  order: string[]
}

export type DemoSite = {
  id: number
  slug: string
  prospect_id?: number | null
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
  /** CMS handover state: not_invited / pending / joined (null until first observed). */
  storyblok_collaborator_status?: StoryblokCollaboratorStatus | null
  storyblok_joined_at?: string | null
  /** When the demo link was first emailed — null until then (TTL not started). */
  demo_link_sent_at?: string | null
  /** Operator's manual "good to send" sign-off from the campaign forecast (null until reviewed). */
  site_reviewed_at?: string | null
  expires_at: string
  created_at: string
  error_message?: string | null
  theme?: DemoSiteTheme | null
  use_brand_color?: boolean
  /** Colour extracted from the prospect logo (detail/update responses), for the Logo pill. */
  brand_color?: string | null
  video_status?: DemoSiteVideoStatus | null
  video_error?: string | null
  video_generated_at?: string | null
  video_page_url?: string | null
  video_thumbnail_url?: string | null
}

/** Lifecycle of a demo site's prospection video (null = never generated). */
export type DemoSiteVideoStatus = 'pending' | 'generating' | 'ready' | 'failed'

/** Where the client stands on the Storyblok CMS handover (null until first observed). */
export type StoryblokCollaboratorStatus = 'not_invited' | 'pending' | 'joined' | 'unknown'

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
   * Record (or clear) the operator's manual "good to send" sign-off for a site.
   *
   * Distinct from {@link verifyDemoSite} (the automated live-URL check): this is the review
   * ticked from the campaign forecast after eyeballing the site, ahead of the automatic send.
   * @param demoSiteId - Id of the demo site.
   * @param reviewed - True to sign off, false to reset.
   * @returns The updated demo site (carrying ``site_reviewed_at``).
   */
  static async setSiteReviewed(demoSiteId: number, reviewed: boolean): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/review`, { reviewed })
  }

  /**
   * Update demo site fields and regenerate its content.
   */
  static async updateDemoSite(demoSiteId: number, payload: DemoSiteUpdatePayload): Promise<DemoSite> {
    return ApiClient.patch<DemoSite>(`${BASE_URL}/${demoSiteId}`, payload)
  }

  /**
   * Fetch the editable section cards (food « Nos spécialités »), their curation state and the labelled photo pool.
   * @param demoSiteId - Id of the demo site.
   * @returns The section state.
   */
  static async getDemoSiteServiceCards(demoSiteId: number): Promise<DemoSiteServiceCards> {
    return ApiClient.get<DemoSiteServiceCards>(`${BASE_URL}/${demoSiteId}/service-cards`)
  }

  /**
   * Ask the AI to compose the section cards from the prospect's photos, menus and reviews (nothing is saved).
   * @param demoSiteId - Id of the demo site.
   * @returns The suggested cards, the refreshed photo pool and the analysis summary.
   */
  static async suggestDemoSiteServiceCards(demoSiteId: number): Promise<DemoSiteServiceCardsSuggestionResult> {
    return ApiClient.post<DemoSiteServiceCardsSuggestionResult>(`${BASE_URL}/${demoSiteId}/service-cards/suggest`, {})
  }

  /**
   * Rebuild demo site content from stored fields without changing them.
   */
  static async regenerateDemoSite(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/regenerate`, {})
  }

  /**
   * Fetch the site's photo pool and current placement (hero/about/gallery by order).
   * @param demoSiteId - Id of the demo site.
   */
  static async getDemoSiteImages(demoSiteId: number): Promise<DemoSiteImages> {
    return ApiClient.get<DemoSiteImages>(`${BASE_URL}/${demoSiteId}/images`)
  }

  /**
   * Save a curated photo placement and regenerate the site so it goes live.
   * @param demoSiteId - Id of the demo site.
   * @param order - Photo URLs in placement order: [0] hero, [1] about, [2:] gallery; omitted = unused.
   * @returns The regenerated demo site.
   */
  static async updateDemoSiteImages(demoSiteId: number, order: string[]): Promise<DemoSite> {
    return ApiClient.put<DemoSite>(`${BASE_URL}/${demoSiteId}/images`, { order })
  }

  /**
   * Send a Storyblok CMS invitation to the demo site client.
   */
  static async inviteDemoSiteClientToCms(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/invite-cms`, {})
  }

  /**
   * Re-read whether the client has joined the Storyblok CMS space (invited → pending → joined).
   * @param demoSiteId - Id of the demo site.
   */
  static async refreshDemoSiteCmsStatus(demoSiteId: number): Promise<DemoSite> {
    return ApiClient.post<DemoSite>(`${BASE_URL}/${demoSiteId}/refresh-cms-status`, {})
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
   * Fetch the context the desktop sidecar needs to render the video background.
   * @param demoSiteId - Id of the demo site.
   * @returns The demo url, Storyblok space/story ids and target durations.
   */
  static async getVideoBackgroundContext(demoSiteId: number): Promise<DemoSiteVideoBackgroundContext> {
    return ApiClient.get<DemoSiteVideoBackgroundContext>(`${BASE_URL}/${demoSiteId}/video-background-context`)
  }

  /**
   * Upload a desktop-produced video background (site scroll + Storyblok editor).
   *
   * The shared api client only handles JSON, so this posts the multipart body
   * directly with the auth token.
   * @param demoSiteId - Id of the demo site.
   * @param clip - The rendered background mp4.
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadVideoBackground(demoSiteId: number, clip: Blob): Promise<void> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const formData: FormData = new FormData()
    formData.append('file', clip, `${demoSiteId}-background.mp4`)
    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}/${demoSiteId}/video-background`, {
      method: 'POST',
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
      body: formData,
    })
    if (!response.ok) {
      const errorText: string = await response.text().catch(() => '')
      let errorMessage: string = `Envoi du fond vidéo échoué : ${response.statusText}`
      if (errorText) {
        try {
          errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
        } catch {
          errorMessage = errorText
        }
      }
      throw new Error(errorMessage)
    }
  }

  /**
   * Fetch the user's presenter clip as a blob, to hand to the desktop montage.
   *
   * The clip is stored on R2 and streamed by an authed endpoint; the sidecar has
   * no auth, so the app fetches it and forwards the bytes.
   * @returns The presenter mp4 blob.
   * @throws When no presenter clip is available.
   */
  static async fetchPresenterVideoFile(): Promise<Blob> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const response: Response = await fetch(`${config.public.apiBase}/api/v1/settings/presenter-video/file`, {
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    if (!response.ok) {
      throw new Error("Clip de présentation introuvable — enregistrez-le d'abord dans les Paramètres.")
    }
    return response.blob()
  }

  /**
   * Upload a desktop-produced FINAL video bundle (zip: video.mp4 + thumbnail.jpg).
   *
   * The sidecar does the whole montage locally; the API just stores it and marks
   * the site ready. Multipart, so it bypasses the JSON api client.
   * @param demoSiteId - Id of the demo site.
   * @param bundle - The zip produced by the sidecar.
   * @returns The updated demo site.
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadFinalVideo(demoSiteId: number, bundle: Blob): Promise<DemoSite> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const formData: FormData = new FormData()
    formData.append('file', bundle, `${demoSiteId}-video.zip`)
    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}/${demoSiteId}/video-final`, {
      method: 'POST',
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
      body: formData,
    })
    if (!response.ok) {
      const errorText: string = await response.text().catch(() => '')
      let errorMessage: string = `Envoi de la vidéo échoué : ${response.statusText}`
      if (errorText) {
        try {
          errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
        } catch {
          errorMessage = errorText
        }
      }
      throw new Error(errorMessage)
    }
    return (await response.json()) as DemoSite
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
   * Whether the 21-day countdown has not started yet (demo link not emailed).
   */
  static isTtlPending(site: DemoSite): boolean {
    return !site.demo_link_sent_at
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
   * Append the internal-visit flag so the owner's own opens are excluded from tracking.
   * Only for a link WE click to view a demo — never a copied/shared link sent to a prospect.
   */
  static withInternalFlag(url: string | null | undefined): string | null {
    if (!url) {
      return null
    }
    const separator: string = url.includes('?') ? '&' : '?'
    return `${url}${separator}internal=1`
  }

  /**
   * Whether the demo site is reachable (prod URL or local fallback).
   */
  static isDemoSiteReachable(site: DemoSite): boolean {
    return Boolean(site.demo_url_live || site.local_demo_url)
  }
}
