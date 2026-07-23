import { ApiClient } from './api'

/** A single timeline entry of demo behaviour. */
export type BehaviorTimelineEntry = {
  type: string
  label: string
  timestamp: string | null
  properties: Record<string, unknown>
}

/** Lead score + behaviour timeline for a prospect. */
export type ProspectBehavior = {
  temperature: string
  score: number
  signals: Record<string, number | string | null>
  timeline: BehaviorTimelineEntry[]
  has_data: boolean
  tracking_configured: boolean
}

/** AI (or rule-based) behaviour summary. */
export type BehaviorSummary = {
  summary: string
}

/** A behaviour-personalised follow-up draft. */
export type PersonalizedFollowup = {
  subject: string
  body_html: string
}

/** Result of a one-off email send. */
export type QuickSendResult = {
  success: boolean
  email_log_id?: number
  message_id?: string
  error?: string
}

export class BehaviorService {
  /**
   * Fetch the lead score, signals and behaviour timeline for a prospect.
   * @param prospectId - Target prospect id.
   * @returns The behaviour payload.
   */
  static async getProspectBehavior(prospectId: number): Promise<ProspectBehavior> {
    return ApiClient.get<ProspectBehavior>(`/api/v1/prospects/${prospectId}/behavior`)
  }

  /**
   * Generate an AI (or rule-based) read of the prospect's demo behaviour.
   * @param prospectId - Target prospect id.
   * @returns The summary text.
   */
  static async summarizeProspectBehavior(prospectId: number): Promise<BehaviorSummary> {
    return ApiClient.post<BehaviorSummary>(`/api/v1/prospects/${prospectId}/behavior/summary`, {})
  }

  /**
   * Draft a behaviour-personalised follow-up email for a prospect.
   * @param prospectId - Target prospect id.
   * @returns The drafted subject and HTML body.
   */
  static async draftPersonalizedFollowup(prospectId: number): Promise<PersonalizedFollowup> {
    return ApiClient.post<PersonalizedFollowup>(`/api/v1/prospects/${prospectId}/personalized-followup`, {})
  }

  /**
   * Send a one-off email via the user's Resend configuration.
   * @param payload - Recipient, subject and body.
   * @returns The send result.
   */
  static async sendQuickEmail(payload: {
    recipient_email: string
    recipient_name?: string | null
    subject: string
    body_html: string
    prospect_id?: string | null
  }): Promise<QuickSendResult> {
    return ApiClient.post<QuickSendResult>('/api/v1/emails/quick-send', payload)
  }
}
