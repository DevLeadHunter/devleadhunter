import type { EmailData, BulkEmailData } from '~/types'
import { api } from './api'

/**
 * Email service for sending individual and bulk emails
 * @module services/emailService
 */

/**
 * Send individual email to a prospect
 * @param {EmailData} data - Email data
 * @returns {Promise<void>} Promise that resolves when email is sent
 * @throws {Error} If email sending fails
 *
 * @example
 * ```typescript
 * await sendEmail({
 *   to: 'prospect@example.com',
 *   subject: 'Website Development Services',
 *   body: 'Hello...',
 *   prospectId: '123'
 * });
 * ```
 */
export async function sendEmail(data: EmailData): Promise<void> {
  try {
    await api.post('/api/emails/send', data)
  } catch (error) {
    console.error('Failed to send email:', error)
    throw error
  }
}

/**
 * Send bulk emails to a campaign
 * @param {BulkEmailData} data - Bulk email data
 * @returns {Promise<void>} Promise that resolves when emails are sent
 * @throws {Error} If bulk email sending fails
 *
 * @example
 * ```typescript
 * await sendBulkEmail({
 *   campaignId: 'campaign-123',
 *   subject: 'Special Offer',
 *   body: 'Hello...'
 * });
 * ```
 */
export async function sendBulkEmail(data: BulkEmailData): Promise<void> {
  try {
    await api.post('/api/emails/bulk', data)
  } catch (error) {
    console.error('Failed to send bulk emails:', error)
    throw error
  }
}
