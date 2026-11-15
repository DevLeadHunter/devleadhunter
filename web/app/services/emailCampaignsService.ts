/**
 * Email campaigns service for sending emails to prospects.
 * @module services/emailCampaignsService
 */

import type { EmailLog, EmailStats } from '~/types'
import { ApiClient } from './api'

export class EmailCampaignsService {
  /**
   * Get email logs with optional filters
   */
  static async getEmailLogs(params?: {
    campaign_id?: string
    prospect_id?: string
    status?: string
    module_key?: string
    limit?: number
    offset?: number
  }): Promise<{ total: number; logs: EmailLog[] }> {
    try {
      return await ApiClient.get<{ total: number; logs: EmailLog[] }>('/api/v1/emails/logs', { params })
    } catch (error) {
      console.error('Failed to get email logs:', error)
      throw error
    }
  }

  /**
   * Get a specific email log by ID
   */
  static async getEmailLog(logId: number): Promise<EmailLog> {
    try {
      return await ApiClient.get<EmailLog>(`/api/v1/emails/logs/${logId}`)
    } catch (error) {
      console.error('Failed to get email log:', error)
      throw error
    }
  }

  /**
   * Get email statistics of one product module
   * @param moduleKey - The module whose emails are counted.
   * @param campaignId - Count the emails of this campaign only.
   * @returns The totals and rates of those emails.
   */
  static async getEmailStats(moduleKey: string, campaignId?: string): Promise<EmailStats> {
    try {
      return await ApiClient.get<EmailStats>('/api/v1/emails/stats', {
        params: { module_key: moduleKey, campaign_id: campaignId },
      })
    } catch (error) {
      console.error('Failed to get email stats:', error)
      throw error
    }
  }
}
