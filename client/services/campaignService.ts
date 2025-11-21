/**
 * Campaign service for API communication
 * @module services/campaignService
 */
import type { Campaign } from '~/types';
import { $api } from './api';

export interface CampaignCreateData {
  name: string;
  description?: string;
  status?: string;
  prospect_ids?: number[];
}

export interface CampaignUpdateData {
  name?: string;
  description?: string;
  status?: string;
}

export interface CampaignResponse {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
  prospects_count: number;
}

export interface CampaignDetailResponse extends CampaignResponse {
  prospects: Array<{
    id: number;
    name: string;
    email?: string;
    phone?: string;
    city?: string;
    category: string;
    source: string;
    confidence: number;
  }>;
}

export interface CampaignListResponse {
  campaigns: CampaignResponse[];
  total: number;
}

export interface CampaignStats {
  campaign_id: number;
  total_prospects: number;
  total_emails_sent: number;
  emails_delivered: number;
  emails_opened: number;
  emails_clicked: number;
  emails_bounced: number;
  emails_failed: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
}

/**
 * Campaign service for managing email campaigns
 */
export const campaignService = {
  /**
   * Create a new campaign
   */
  async create(data: CampaignCreateData): Promise<CampaignDetailResponse> {
    const response = await $api<CampaignDetailResponse>('/campaigns', {
      method: 'POST',
      body: data
    });
    return response;
  },

  /**
   * Get all campaigns
   */
  async list(skip = 0, limit = 100, status?: string): Promise<CampaignListResponse> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString()
    });
    
    if (status) {
      params.append('status', status);
    }
    
    const response = await $api<CampaignListResponse>(`/campaigns?${params.toString()}`);
    return response;
  },

  /**
   * Get campaign details by ID
   */
  async get(id: number): Promise<CampaignDetailResponse> {
    const response = await $api<CampaignDetailResponse>(`/campaigns/${id}`);
    return response;
  },

  /**
   * Update campaign
   */
  async update(id: number, data: CampaignUpdateData): Promise<CampaignResponse> {
    const response = await $api<CampaignResponse>(`/campaigns/${id}`, {
      method: 'PATCH',
      body: data
    });
    return response;
  },

  /**
   * Delete campaign
   */
  async delete(id: number): Promise<void> {
    await $api(`/campaigns/${id}`, {
      method: 'DELETE'
    });
  },

  /**
   * Add prospects to campaign
   */
  async addProspects(campaignId: number, prospectIds: number[]): Promise<CampaignDetailResponse> {
    const response = await $api<CampaignDetailResponse>(`/campaigns/${campaignId}/prospects`, {
      method: 'POST',
      body: { prospect_ids: prospectIds }
    });
    return response;
  },

  /**
   * Remove prospect from campaign
   */
  async removeProspect(campaignId: number, prospectId: number): Promise<CampaignDetailResponse> {
    const response = await $api<CampaignDetailResponse>(`/campaigns/${campaignId}/prospects/${prospectId}`, {
      method: 'DELETE'
    });
    return response;
  },

  /**
   * Get campaign statistics
   */
  async getStats(campaignId: number): Promise<CampaignStats> {
    const response = await $api<CampaignStats>(`/campaigns/${campaignId}/stats`);
    return response;
  }
};

