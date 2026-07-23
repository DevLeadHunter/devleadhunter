/**
 * Campaign service — HTTP client for the /campaigns API routes.
 * @module services/campaignService
 */
import { ApiClient } from './api'
import type { CampaignFollowUp, CampaignVariantStats } from '~/types'

export type CampaignStatus = 'draft' | 'active' | 'completed' | 'paused' | 'cancelled'

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

export type CampaignResponse = {
  id: number
  user_id: number
  name: string
  description?: string | null
  status: CampaignStatus
  template_id?: number | null
  ab_template_id_b?: number | null
  send_delay_minutes: number
  follow_up_delay_days: number
  behavior_personalized_followups: boolean
  started_at?: string | null
  created_at: string
  updated_at?: string | null
  prospects_count: number
}

export interface CampaignDetailResponse extends CampaignResponse {
  prospects: CampaignProspect[]
  follow_ups: CampaignFollowUp[]
}

export type CampaignListResponse = {
  campaigns: CampaignResponse[]
  total: number
}

export type CampaignStats = {
  campaign_id: number
  total_prospects: number
  total_emails_sent: number
  emails_delivered: number
  emails_opened: number
  emails_clicked: number
  emails_bounced: number
  emails_failed: number
  delivery_rate: number
  open_rate: number
  click_rate: number
  ab_stats?: CampaignVariantStats[] | null
}

export type CampaignCreatePayload = {
  name: string
  description?: string
  status?: CampaignStatus
  prospect_ids?: number[]
  template_id?: number
  ab_template_id_b?: number
  send_delay_minutes?: number
}

export type CampaignUpdatePayload = {
  name?: string
  description?: string
  status?: CampaignStatus
}

export type CampaignSettingsPayload = {
  template_id?: number | null
  ab_template_id_b?: number | null
  disable_ab?: boolean
  send_delay_minutes?: number
  behavior_personalized_followups?: boolean
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
}

export type CampaignQueueResponse = {
  pending_count: number
  items: CampaignQueueItem[]
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
}
