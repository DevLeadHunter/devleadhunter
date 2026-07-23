/**
 * Email templates service for managing email templates.
 * @module services/emailTemplatesService
 */

import type { EmailTemplate, EmailTemplateCreate, EmailTemplateUpdate } from '~/types'
import { ApiClient } from './api'

export class EmailTemplatesService {
  /**
   * Get all email templates for the current user
   */
  static async getEmailTemplates(): Promise<EmailTemplate[]> {
    try {
      return await ApiClient.get<EmailTemplate[]>('/api/v1/email-templates')
    } catch (error) {
      console.error('Failed to get email templates:', error)
      throw error
    }
  }

  /**
   * Get a specific email template by ID
   */
  static async getEmailTemplate(id: number): Promise<EmailTemplate> {
    try {
      return await ApiClient.get<EmailTemplate>(`/api/v1/email-templates/${id}`)
    } catch (error) {
      console.error('Failed to get email template:', error)
      throw error
    }
  }

  /**
   * Create a new email template
   */
  static async createEmailTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
    try {
      return await ApiClient.post<EmailTemplate>('/api/v1/email-templates', data)
    } catch (error) {
      console.error('Failed to create email template:', error)
      throw error
    }
  }

  /**
   * Update an email template
   */
  static async updateEmailTemplate(templateId: number, data: EmailTemplateUpdate): Promise<EmailTemplate> {
    try {
      return await ApiClient.patch<EmailTemplate>(`/api/v1/email-templates/${templateId}`, data)
    } catch (error) {
      console.error('Failed to update email template:', error)
      throw error
    }
  }

  /**
   * Delete an email template
   */
  static async deleteEmailTemplate(templateId: number): Promise<void> {
    try {
      await ApiClient.delete(`/api/v1/email-templates/${templateId}`)
    } catch (error) {
      console.error('Failed to delete email template:', error)
      throw error
    }
  }

  /**
   * Preview an email template with variable substitution
   */
  static async previewEmailTemplate(
    templateId: number,
    variables: Record<string, string>,
  ): Promise<{ subject: string; body_html: string }> {
    try {
      return await ApiClient.post<{ subject: string; body_html: string }>('/api/v1/email-templates/preview', {
        template_id: templateId,
        variables,
      })
    } catch (error) {
      console.error('Failed to preview email template:', error)
      throw error
    }
  }
}
