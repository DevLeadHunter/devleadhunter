/**
 * Campaign service — HTTP client for the /campaigns API routes.
 * @module services/campaignService
 */
import { $api } from './api'
import type { CampaignFollowUp, CampaignVariantStats } from '~/types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Allowed campaign status values. */
export type CampaignStatus = 'draft' | 'active' | 'completed' | 'paused' | 'cancelled'

/** Allowed queue item status values. */
export type QueueItemStatus = 'pending' | 'sending' | 'sent' | 'skipped' | 'failed'

export interface CampaignProspect {
  id: number
  name: string
  email?: string | null
  phone?: string | null
  city?: string | null
  category: string
  source: string
  confidence: number
  /** A/B variant assigned at enqueue time (null before launch). */
  ab_variant?: string | null
}

export interface CampaignResponse {
  id: number
  user_id: number
  name: string
  description?: string | null
  status: CampaignStatus
  /** J1 template ID (variant A). */
  template_id?: number | null
  /** J1 template ID for variant B (A/B testing). */
  ab_template_id_b?: number | null
  send_delay_minutes: number
  follow_up_delay_days: number
  started_at?: string | null
  created_at: string
  updated_at?: string | null
  prospects_count: number
}

export interface CampaignDetailResponse extends CampaignResponse {
  prospects: CampaignProspect[]
  follow_ups: CampaignFollowUp[]
}

export interface CampaignListResponse {
  campaigns: CampaignResponse[]
  total: number
}

export interface CampaignStats {
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
  /** Populated only when the campaign has an A/B template. */
  ab_stats?: CampaignVariantStats[] | null
}

export interface CampaignCreateData {
  name: string
  description?: string
  status?: CampaignStatus
  prospect_ids?: number[]
  template_id?: number
  ab_template_id_b?: number
  send_delay_minutes?: number
}

export interface CampaignUpdateData {
  name?: string
  description?: string
  status?: CampaignStatus
}

export interface CampaignSettingsData {
  template_id?: number | null
  ab_template_id_b?: number | null
  /** Explicitly turn A/B off (since null means "unchanged"). */
  disable_ab?: boolean
  send_delay_minutes?: number
  follow_ups?: Array<{ template_id: number; delay_days: number; position: number }>
}

export interface LaunchCampaignData {
  template_id?: number
  ab_template_id_b?: number
  follow_up_template_id?: number
  follow_up_delay_days?: number
  send_delay_minutes?: number
}

export interface LaunchCampaignResponse {
  success: boolean
  enqueued: number
  message: string
}

/** A single item in the campaign send queue. */
export interface CampaignQueueItem {
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

export interface CampaignQueueResponse {
  pending_count: number
  items: CampaignQueueItem[]
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const campaignService = {
  /**
   * Create a new campaign.
   * @param data - Campaign creation payload.
   */
  async create(data: CampaignCreateData): Promise<CampaignDetailResponse> {
    return $api<CampaignDetailResponse>('/campaigns', { method: 'POST', body: data })
  },

  /**
   * List campaigns with optional status filtering.
   * @param skip   - Pagination offset.
   * @param limit  - Max records to return.
   * @param status - Optional status filter.
   */
  async list(skip = 0, limit = 100, status?: CampaignStatus): Promise<CampaignListResponse> {
    const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() })
    if (status) params.append('status', status)
    return $api<CampaignListResponse>(`/campaigns?${params.toString()}`)
  },

  /**
   * Fetch a campaign by ID including prospects and follow-up sequence.
   * @param id - Campaign ID.
   */
  async get(id: number): Promise<CampaignDetailResponse> {
    return $api<CampaignDetailResponse>(`/campaigns/${id}`)
  },

  /**
   * Update a campaign's name, description, or status.
   * @param id   - Campaign ID.
   * @param data - Fields to update.
   */
  async update(id: number, data: CampaignUpdateData): Promise<CampaignDetailResponse> {
    return $api<CampaignDetailResponse>(`/campaigns/${id}`, { method: 'PATCH', body: data })
  },

  /**
   * Update campaign send configuration (template, account, A/B, follow-ups).
   * Safe to call on active campaigns — changes apply to unsent items.
   * @param id       - Campaign ID.
   * @param settings - Configuration to update.
   */
  async updateSettings(id: number, settings: CampaignSettingsData): Promise<CampaignDetailResponse> {
    return $api<CampaignDetailResponse>(`/campaigns/${id}/settings`, {
      method: 'PATCH',
      body: settings,
    })
  },

  /**
   * Permanently delete a campaign.
   * @param id - Campaign ID.
   */
  async delete(id: number): Promise<void> {
    await $api(`/campaigns/${id}`, { method: 'DELETE' })
  },

  /**
   * Add prospects to a campaign.
   * @param campaignId  - Campaign ID.
   * @param prospectIds - IDs of prospects to add.
   */
  async addProspects(campaignId: number, prospectIds: number[]): Promise<CampaignDetailResponse> {
    return $api<CampaignDetailResponse>(`/campaigns/${campaignId}/prospects`, {
      method: 'POST',
      body: { prospect_ids: prospectIds },
    })
  },

  /**
   * Remove a single prospect from a campaign.
   * @param campaignId - Campaign ID.
   * @param prospectId - Prospect ID to remove.
   */
  async removeProspect(campaignId: number, prospectId: number): Promise<CampaignDetailResponse> {
    return $api<CampaignDetailResponse>(`/campaigns/${campaignId}/prospects/${prospectId}`, {
      method: 'DELETE',
    })
  },

  /**
   * Fetch aggregated statistics for a campaign (includes A/B breakdown when applicable).
   * @param campaignId - Campaign ID.
   */
  async getStats(campaignId: number): Promise<CampaignStats> {
    return $api<CampaignStats>(`/campaigns/${campaignId}/stats`)
  },

  /**
   * Launch a campaign — populates the rate-limited send queue.
   * Uses the campaign's stored template/account when request fields are omitted.
   * @param campaignId - Campaign ID.
   * @param data       - Optional overrides for template, account, timing.
   */
  async launch(campaignId: number, data: LaunchCampaignData = {}): Promise<LaunchCampaignResponse> {
    return $api<LaunchCampaignResponse>(`/campaigns/${campaignId}/launch`, {
      method: 'POST',
      body: data,
    })
  },

  /**
   * Pause a running campaign — cancels all pending queue items.
   * @param campaignId - Campaign ID.
   */
  async pause(campaignId: number): Promise<{ success: boolean; cancelled: number }> {
    return $api<{ success: boolean; cancelled: number }>(`/campaigns/${campaignId}/pause`, {
      method: 'POST',
    })
  },

  /**
   * Resume a paused campaign — re-enqueues prospects not yet contacted.
   * @param campaignId - Campaign ID.
   */
  async resume(campaignId: number): Promise<{ success: boolean; enqueued: number }> {
    return $api<{ success: boolean; enqueued: number }>(`/campaigns/${campaignId}/resume`, {
      method: 'POST',
    })
  },

  /**
   * Immediately dispatch a follow-up email to a prospect (bypass delay).
   * Sends via the user's Resend configuration.
   * @param campaignId - Campaign ID.
   * @param prospectId - Prospect to target.
   * @param templateId - Template to use.
   */
  async sendNow(
    campaignId: number,
    prospectId: number,
    templateId: number,
  ): Promise<{ success: boolean; email_log_id?: number; error?: string }> {
    return $api(`/campaigns/${campaignId}/send-now`, {
      method: 'POST',
      body: { prospect_id: prospectId, template_id: templateId },
    })
  },

  /**
   * Fetch the send queue for a campaign.
   * @param campaignId - Campaign ID.
   * @param params     - Optional filters and pagination.
   */
  async getQueue(
    campaignId: number,
    params?: { status?: QueueItemStatus; limit?: number; offset?: number },
  ): Promise<CampaignQueueResponse> {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    return $api<CampaignQueueResponse>(`/campaigns/${campaignId}/queue?${qs.toString()}`)
  },
}
