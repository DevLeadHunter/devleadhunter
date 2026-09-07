import { ApiClient } from './api'

/** The user's SMS sender configuration (a configured sender = channel on) + automation opt-ins. */
export type SmsConfig = {
  sender: string
  provider_ready: boolean
  cold_sms_enabled: boolean
  auto_relance_enabled: boolean
  auto_relance_after_days: number
  relance_template_key: string
}

/** Payload to update the SMS sender (empty sender disables the channel). */
export type SmsConfigUpdate = {
  sender: string
}

/** Payload to toggle the SMS automations (cold-SMS + auto-relance). */
export type SmsAutomationUpdate = {
  cold_sms_enabled: boolean
  auto_relance_enabled: boolean
  auto_relance_after_days: number
  relance_template_key?: string
}

/** A prospect eligible for an SMS relance. */
export type SmsRelanceCandidate = {
  prospect_id: number
  name: string
  city: string | null
  phone: string | null
  demo_url: string
  emailed_at: string
}

/** Outcome of a single relance send. */
export type SmsSendResult = {
  sent: boolean
  reason: string | null
}

/** Outcome of a bulk relance send. */
export type SmsBulkSendResult = {
  sent: number
  skipped: number
}

/** Lifecycle status of a sent SMS. */
export type SmsStatus = 'pending' | 'sent' | 'delivered' | 'failed'

/** One sent SMS in the history (« Suivi des SMS »). */
export type SmsMessage = {
  id: number
  prospect_id: number | null
  recipient_name: string | null
  to_e164: string
  sender: string
  body: string
  status: SmsStatus
  status_detail: string | null
  segments: number
  price_cents: number | null
  error: string | null
  created_at: string
  delivered_at: string | null
}

/** A page of the SMS history. */
export type SmsMessagesResponse = {
  total: number
  messages: SmsMessage[]
}

/** Aggregate counters of the SMS channel. */
export type SmsStats = {
  total: number
  sent: number
  delivered: number
  failed: number
  pending: number
  cost_cents: number
}

/** The platform smsmode account's remaining credit balance (admin-only). */
export type SmsCredit = {
  configured: boolean
  credits: number | null
}

/** Payload to send one free-text SMS (manual composer / self-test). */
export type SmsManualSendPayload = {
  to: string
  text: string
  prospect_id?: number | null
  recipient_name?: string | null
}

/** Which touch of the SMS sequence a library template is written for. */
export type SmsTemplateCategory = 'first_contact' | 'follow_up'

/** One template of the SMS library (defined in the API, one angle per message). */
export type SmsTemplate = {
  key: string
  name: string
  category: SmsTemplateCategory
  body: string
  variables: string[]
  is_default: boolean
}

/** A library template rendered for one prospect (STOP mention excluded, appended at send). */
export type SmsTemplatePreview = {
  key: string
  body: string
  segments: number
}

/** SMS relance channel — sender config, eligible prospects, sending. */
export class SmsService {
  /**
   * Fetch the current user's SMS sender configuration.
   * @returns The SMS config.
   */
  static async getConfig(): Promise<SmsConfig> {
    return ApiClient.get<SmsConfig>('/api/v1/sms/config')
  }

  /**
   * Update the SMS sender + enable flag.
   * @param payload - The new configuration.
   * @returns The saved configuration.
   */
  static async updateConfig(payload: SmsConfigUpdate): Promise<SmsConfig> {
    return ApiClient.put<SmsConfig>('/api/v1/sms/config', payload)
  }

  /**
   * Toggle the SMS automations (cold-SMS + auto-relance).
   * @param payload - The automation opt-ins.
   * @returns The saved configuration.
   */
  static async updateAutomation(payload: SmsAutomationUpdate): Promise<SmsConfig> {
    return ApiClient.put<SmsConfig>('/api/v1/sms/config/automation', payload)
  }

  /**
   * List prospects eligible for an SMS relance.
   * @param afterDays - Minimum age in days of the unanswered email.
   * @returns The eligible candidates.
   */
  static async listCandidates(afterDays: number = 30): Promise<SmsRelanceCandidate[]> {
    return ApiClient.get<SmsRelanceCandidate[]>(`/api/v1/sms/relance-candidates?after_days=${afterDays}`)
  }

  /**
   * Send a relance SMS to one prospect.
   * @param prospectId - The prospect id.
   * @returns The send result.
   */
  static async sendRelance(prospectId: number): Promise<SmsSendResult> {
    return ApiClient.post<SmsSendResult>(`/api/v1/sms/relance/${prospectId}`, {})
  }

  /**
   * Send relance SMS to all eligible prospects, up to a limit.
   * @param limit - Maximum number to send.
   * @returns The bulk send result.
   */
  static async sendRelanceBulk(limit: number = 20): Promise<SmsBulkSendResult> {
    return ApiClient.post<SmsBulkSendResult>(`/api/v1/sms/relance?limit=${limit}`, {})
  }

  /**
   * Fetch the sent-SMS history (newest first).
   * @param limit - Maximum rows to return.
   * @returns The history page.
   */
  static async listMessages(limit: number = 500): Promise<SmsMessagesResponse> {
    return ApiClient.get<SmsMessagesResponse>(`/api/v1/sms/messages?limit=${limit}`)
  }

  /**
   * Fetch the aggregate counters of the SMS channel.
   * @returns The stats.
   */
  static async getStats(): Promise<SmsStats> {
    return ApiClient.get<SmsStats>('/api/v1/sms/stats')
  }

  /**
   * Fetch the platform smsmode account's remaining credit balance (admin-only).
   * @returns The remaining credits (null when unreadable) and whether smsmode is configured.
   */
  static async getCredit(): Promise<SmsCredit> {
    return ApiClient.get<SmsCredit>('/api/v1/sms/credit')
  }

  /**
   * Send one free-text SMS to a number (manual composer / self-test).
   * @param payload - Recipient number, message, and optional prospect link.
   * @returns The send result.
   */
  static async sendManual(payload: SmsManualSendPayload): Promise<SmsSendResult> {
    return ApiClient.post<SmsSendResult>('/api/v1/sms/send', payload)
  }

  /**
   * List the SMS template library, optionally narrowed to one touch.
   * @param category - First contact or follow-up; omitted = the whole library.
   * @returns The templates, in library order.
   */
  static async listTemplates(category?: SmsTemplateCategory): Promise<SmsTemplate[]> {
    const query: string = category ? `?category=${category}` : ''
    return ApiClient.get<SmsTemplate[]>(`/api/v1/sms/templates${query}`)
  }

  /**
   * Render a library template for one prospect (his greeting, his business, his demo link).
   * @param key - The template key.
   * @param prospectId - The prospect to render for.
   * @returns The rendered body and the segments it will bill.
   */
  static async previewTemplate(key: string, prospectId: number): Promise<SmsTemplatePreview> {
    return ApiClient.get<SmsTemplatePreview>(`/api/v1/sms/templates/${key}/preview?prospect_id=${prospectId}`)
  }
}
