/**
 * Campaign service — HTTP client for the /campaigns API routes.
 * @module services/campaignService
 */
import { ApiClient } from './api'
import type { CampaignFollowUp, CampaignVariantStats } from '~/types'

export type CampaignStatus = 'draft' | 'active' | 'completed' | 'paused' | 'cancelled'

/** Send channel of a campaign. "email" uses templates/Resend; "sms" sends a cold SMS with the demo link. */
export type CampaignChannel = 'email' | 'sms'

export type QueueItemStatus = 'pending' | 'sending' | 'sent' | 'skipped' | 'failed'

export type CampaignProspect = {
  id: number
  name: string
  email?: string | null
  phone?: string | null
  city?: string | null
  category: string
  source: string
  confidence: number
  ab_variant?: string | null
}

/** A campaign a prospect already belongs to — shown as a badge in the add-prospects picker. */
export type CampaignProspectMembership = {
  id: number
  name: string
}

export type CampaignResponse = {
  id: number
  user_id: number
  name: string
  description?: string | null
  status: CampaignStatus
  channel: CampaignChannel
  template_id?: number | null
  ab_template_id_b?: number | null
  /** SMS campaigns only: chosen first-contact library template key (null = default). */
  sms_template_key?: string | null
  send_delay_minutes: number
  follow_up_delay_days: number
  behavior_personalized_followups: boolean
  include_video: boolean
  max_emails_per_day?: number | null
  started_at?: string | null
  created_at: string
  updated_at?: string | null
  prospects_count: number
  /** Earliest still-pending send in the queue (naive UTC), or null when nothing is queued. */
  next_send_at?: string | null
  /** First scheduled send across the queue (naive UTC), or null before launch. */
  first_send_at?: string | null
  /** Last scheduled send across the queue (naive UTC), or null before launch. */
  last_send_at?: string | null
}

export interface CampaignDetailResponse extends CampaignResponse {
  prospects: CampaignProspect[]
  follow_ups: CampaignFollowUp[]
}

export type CampaignListResponse = {
  campaigns: CampaignResponse[]
  total: number
  /** Count of the user's pending sends scheduled within the next 7 days. */
  upcoming_sends_7d?: number
}

export type CampaignStats = {
  campaign_id: number
  total_prospects: number
  total_emails_sent: number
  emails_delivered: number
  emails_opened: number
  emails_clicked: number
  emails_replied: number
  emails_bounced: number
  emails_failed: number
  delivery_rate: number
  open_rate: number
  click_rate: number
  reply_rate: number
  ab_stats?: CampaignVariantStats[] | null
}

export type CampaignCreatePayload = {
  name: string
  description?: string
  status?: CampaignStatus
  channel?: CampaignChannel
  prospect_ids?: number[]
  template_id?: number
  ab_template_id_b?: number
  sms_template_key?: string
  send_delay_minutes?: number
  max_emails_per_day?: number | null
}

export type CampaignUpdatePayload = {
  name?: string
  description?: string
  status?: CampaignStatus
}

export type CampaignSettingsPayload = {
  template_id?: number | null
  ab_template_id_b?: number | null
  sms_template_key?: string
  disable_ab?: boolean
  send_delay_minutes?: number
  max_emails_per_day?: number | null
  clear_max_emails_per_day?: boolean
  behavior_personalized_followups?: boolean
  include_video?: boolean
  follow_ups?: Array<{ template_id: number; delay_days: number; position: number }>
}

export type CampaignLaunchPayload = {
  template_id?: number
  ab_template_id_b?: number
  follow_up_template_id?: number
  follow_up_delay_days?: number
  send_delay_minutes?: number
}

export type LaunchCampaignResponse = {
  success: boolean
  enqueued: number
  skipped_no_demo?: Array<{ id: number; name: string }>
  message: string
}

/** A single item in the campaign send queue. */
export type CampaignQueueItem = {
  id: number
  queue_type: 'initial' | 'followup'
  status: QueueItemStatus
  scheduled_at: string
  prospect_id: number
  prospect_name?: string | null
  prospect_email?: string | null
  ab_variant?: string | null
  follow_up_index: number
  email_log_id?: number | null
  /** Why a row was skipped (e.g. « Annulé manuellement », « Site démo expiré ») — null otherwise. */
  skip_reason?: string | null
}

export type CampaignQueueResponse = {
  pending_count: number
  items: CampaignQueueItem[]
}

/** Kind of link an email carries — only the website (demo) link exists today. */
export type ForecastLinkKind = 'website'

/** One scheduled send in the week-ahead forecast, across all campaigns. */
export type CampaignForecastItem = {
  queue_id: number
  scheduled_at: string
  campaign_id: number
  campaign_name: string
  prospect_id: number
  prospect_name?: string | null
  prospect_email?: string | null
  prospect_city?: string | null
  prospect_category: string
  queue_type: 'initial' | 'followup'
  follow_up_index: number
  ab_variant?: string | null
  /** 'pending' for an upcoming send; 'skipped' (with skip_reason) for one that will not go out. */
  status: QueueItemStatus
  skip_reason?: string | null
  /** The link the email will carry, its kind, and the reviewable site — null when no active demo. */
  link?: string | null
  link_kind?: ForecastLinkKind | null
  demo_site_id?: number | null
  site_reviewed_at?: string | null
}

export type CampaignForecastResponse = {
  items: CampaignForecastItem[]
  range_start: string
  range_end: string
}

export class CampaignService {
  /**
   * Create a new campaign.
   * @param data - Campaign creation payload.
   */
  static async create(data: CampaignCreatePayload): Promise<CampaignDetailResponse> {
    return ApiClient.post<CampaignDetailResponse>('/api/v1/campaigns', data)
  }

  /**
   * List campaigns with optional status filtering.
   * @param skip   - Pagination offset.
   * @param limit  - Max records to return.
   * @param status - Optional status filter.
   */
  static async list(skip: number = 0, limit: number = 100, status?: CampaignStatus): Promise<CampaignListResponse> {
    const params: URLSearchParams = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() })
    if (status) params.append('status', status)
    return ApiClient.get<CampaignListResponse>(`/api/v1/campaigns?${params.toString()}`)
  }

  /**
   * Fetch a campaign by ID including prospects and follow-up sequence.
   * @param id - Campaign ID.
   */
  static async get(id: number): Promise<CampaignDetailResponse> {
    return ApiClient.get<CampaignDetailResponse>(`/api/v1/campaigns/${id}`)
  }

  /**
   * Update a campaign's name, description, or status.
   * @param id   - Campaign ID.
   * @param data - Fields to update.
   */
  static async update(id: number, data: CampaignUpdatePayload): Promise<CampaignDetailResponse> {
    return ApiClient.patch<CampaignDetailResponse>(`/api/v1/campaigns/${id}`, data)
  }

  /**
   * Update campaign send configuration (template, account, A/B, follow-ups).
   * Safe to call on active campaigns — changes apply to unsent items.
   * @param id       - Campaign ID.
   * @param settings - Configuration to update.
   */
  static async updateSettings(id: number, settings: CampaignSettingsPayload): Promise<CampaignDetailResponse> {
    return ApiClient.patch<CampaignDetailResponse>(`/api/v1/campaigns/${id}/settings`, settings)
  }

  /**
   * Permanently delete a campaign.
   * @param id - Campaign ID.
   */
  static async delete(id: number): Promise<void> {
    await ApiClient.delete(`/api/v1/campaigns/${id}`)
  }

  /**
   * Add prospects to a campaign.
   * @param campaignId  - Campaign ID.
   * @param prospectIds - IDs of prospects to add.
   */
  static async addProspects(campaignId: number, prospectIds: number[]): Promise<CampaignDetailResponse> {
    return ApiClient.post<CampaignDetailResponse>(`/api/v1/campaigns/${campaignId}/prospects`, {
      prospect_ids: prospectIds,
    })
  }

  /**
   * Remove a single prospect from a campaign.
   * @param campaignId - Campaign ID.
   * @param prospectId - Prospect ID to remove.
   */
  static async removeProspect(campaignId: number, prospectId: number): Promise<CampaignDetailResponse> {
    return ApiClient.delete<CampaignDetailResponse>(`/api/v1/campaigns/${campaignId}/prospects/${prospectId}`)
  }

  /**
   * Set the campaign's prospect send order (drag & drop) and re-date the pending queue to match.
   * @param campaignId  - Campaign ID.
   * @param prospectIds - The campaign's prospect ids in their new send order (the full set).
   */
  static async reorderProspects(campaignId: number, prospectIds: number[]): Promise<CampaignDetailResponse> {
    return ApiClient.patch<CampaignDetailResponse>(`/api/v1/campaigns/${campaignId}/prospects/reorder`, {
      prospect_ids: prospectIds,
    })
  }

  /**
   * Fetch, per prospect, the user's campaigns it already belongs to (add-prospects picker badges).
   * @returns A map of prospect id to the campaigns that already contain it.
   */
  static async getProspectMemberships(): Promise<Record<number, CampaignProspectMembership[]>> {
    const response: { memberships: Record<number, CampaignProspectMembership[]> } = await ApiClient.get<{
      memberships: Record<number, CampaignProspectMembership[]>
    }>('/api/v1/campaigns/prospect-memberships')
    return response.memberships
  }

  /**
   * Fetch aggregated statistics for a campaign (includes A/B breakdown when applicable).
   * @param campaignId - Campaign ID.
   */
  static async getStats(campaignId: number): Promise<CampaignStats> {
    return ApiClient.get<CampaignStats>(`/api/v1/campaigns/${campaignId}/stats`)
  }

  /**
   * Launch a campaign — populates the rate-limited send queue.
   * Uses the campaign's stored template/account when request fields are omitted.
   * @param campaignId - Campaign ID.
   * @param data       - Optional overrides for template, account, timing.
   */
  static async launch(campaignId: number, data: CampaignLaunchPayload = {}): Promise<LaunchCampaignResponse> {
    return ApiClient.post<LaunchCampaignResponse>(`/api/v1/campaigns/${campaignId}/launch`, data)
  }

  /**
   * Pause a running campaign — cancels all pending queue items.
   * @param campaignId - Campaign ID.
   */
  static async pause(campaignId: number): Promise<{ success: boolean; cancelled: number }> {
    return ApiClient.post<{ success: boolean; cancelled: number }>(`/api/v1/campaigns/${campaignId}/pause`, {})
  }

  /**
   * Resume a paused campaign — re-enqueues prospects not yet contacted.
   * @param campaignId - Campaign ID.
   */
  static async resume(campaignId: number): Promise<{ success: boolean; enqueued: number }> {
    return ApiClient.post<{ success: boolean; enqueued: number }>(`/api/v1/campaigns/${campaignId}/resume`, {})
  }

  /**
   * Immediately dispatch a follow-up email to a prospect (bypass delay).
   * Sends via the user's Resend configuration.
   * @param campaignId - Campaign ID.
   * @param prospectId - Prospect to target.
   * @param templateId - Template to use.
   */
  static async sendNow(
    campaignId: number,
    prospectId: number,
    templateId: number,
  ): Promise<{ success: boolean; email_log_id?: number; error?: string }> {
    return ApiClient.post(`/api/v1/campaigns/${campaignId}/send-now`, {
      prospect_id: prospectId,
      template_id: templateId,
    })
  }

  /**
   * Cancel a single pending queue item so it is not sent.
   * The item becomes « Ignoré » with a manual reason and can be re-sent later.
   * @param campaignId - Campaign ID.
   * @param queueId    - Queue item ID.
   */
  static async cancelQueueItem(
    campaignId: number,
    queueId: number,
  ): Promise<{ success: boolean; id: number; status: QueueItemStatus }> {
    return ApiClient.post(`/api/v1/campaigns/${campaignId}/queue/${queueId}/cancel`, {})
  }

  /**
   * Re-queue a skipped item so the worker sends it on its next tick (~1 min).
   * @param campaignId - Campaign ID.
   * @param queueId    - Queue item ID.
   */
  static async resendQueueItem(
    campaignId: number,
    queueId: number,
  ): Promise<{ success: boolean; id: number; status: QueueItemStatus; scheduled_at?: string }> {
    return ApiClient.post(`/api/v1/campaigns/${campaignId}/queue/${queueId}/resend`, {})
  }

  /**
   * Fetch the send queue for a campaign.
   * @param campaignId - Campaign ID.
   * @param params     - Optional filters and pagination.
   */
  static async getQueue(
    campaignId: number,
    params?: { status?: QueueItemStatus; limit?: number; offset?: number },
  ): Promise<CampaignQueueResponse> {
    const qs: URLSearchParams = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    return ApiClient.get<CampaignQueueResponse>(`/api/v1/campaigns/${campaignId}/queue?${qs.toString()}`)
  }

  /**
   * Fetch the week-ahead send forecast across all of the user's campaigns.
   * @param startIso - Window start as an ISO datetime (the exact UTC instant of the local week start).
   * @param days     - Window width in days (default 7).
   */
  static async getForecast(startIso: string, days: number = 7): Promise<CampaignForecastResponse> {
    const qs: URLSearchParams = new URLSearchParams({ start: startIso, days: String(days) })
    return ApiClient.get<CampaignForecastResponse>(`/api/v1/campaigns/forecast?${qs.toString()}`)
  }
}
