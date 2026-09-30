import type { ConversationItem, EmailResendResult, PendingReply } from '~/types'
import { ApiClient } from './api'

/**
 * Read/act on individual sent-email logs (the « Suivi des e-mails » page).
 */
export class EmailLogsService {
  /**
   * Re-send an email log's message, optionally to a corrected address.
   * A different address is saved as the prospect's primary, so the pending follow-up reaches it too.
   * @param logId The email log to re-send.
   * @param email Address to send to; when empty, the prospect's current primary address is used.
   * @returns The send result (success flag + optional error).
   */
  static async resendEmailLog(logId: number, email?: string): Promise<EmailResendResult> {
    return ApiClient.post<EmailResendResult>(`/api/v1/emails/logs/${logId}/resend`, {
      email: email && email.trim() ? email.trim() : null,
    })
  }

  /**
   * Fetch the full user↔prospect exchange around a send (oldest first).
   * @param logId Any send belonging to the thread.
   * @returns Ordered conversation items (outbound sends + captured replies).
   */
  static async getConversation(logId: number): Promise<ConversationItem[]> {
    const res: { items: ConversationItem[] } = await ApiClient.get(`/api/v1/emails/logs/${logId}/conversation`)
    return res.items
  }

  /**
   * Fetch the « à traiter » queue: human replies not yet answered.
   * @returns Count + items, newest first.
   */
  static async getPendingReplies(): Promise<{ count: number; items: PendingReply[] }> {
    return ApiClient.get('/api/v1/emails/replies/pending')
  }

  /**
   * Mark a reply as dealt with (e.g. answered from one's own mailbox).
   * @param replyId The reply to mark.
   */
  static async markReplyHandled(replyId: number): Promise<void> {
    await ApiClient.post(`/api/v1/emails/replies/${replyId}/handled`, {})
  }

  /** Mark a demo-banner message as dealt with. */
  static async markDemoLeadHandled(leadId: number): Promise<void> {
    await ApiClient.post(`/api/v1/emails/demo-leads/${leadId}/handled`, {})
  }

  /**
   * Answer a prospect's reply from the app (threaded into their mail client).
   * @param replyId The reply being answered.
   * @param bodyHtml The answer's HTML body.
   * @returns The send result (success flag + optional error).
   */
  static async sendReply(replyId: number, bodyHtml: string): Promise<EmailResendResult> {
    return ApiClient.post<EmailResendResult>(`/api/v1/emails/replies/${replyId}/reply`, { body_html: bodyHtml })
  }

  /**
   * Honour an unsubscribe request expressed in a reply (adds the sender to the
   * unsubscribe list and marks the reply handled). User-validated, one click.
   * @param replyId The reply carrying the request.
   */
  static async unsubscribeFromReply(replyId: number): Promise<void> {
    await ApiClient.post(`/api/v1/emails/replies/${replyId}/unsubscribe`, {})
  }
}
