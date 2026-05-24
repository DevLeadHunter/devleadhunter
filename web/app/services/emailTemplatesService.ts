/**
 * Email templates service for managing email templates.
 * @module services/emailTemplatesService
 */

import type { EmailTemplate, EmailTemplateCreate, EmailTemplateUpdate } from '~/types'
import { api } from './api'

/**
 * Get all email templates for the current user
 */
export async function getEmailTemplates(): Promise<EmailTemplate[]> {
  try {
    return await api.get<EmailTemplate[]>('/api/v1/email-templates')
  } catch (error) {
    console.error('Failed to get email templates:', error)
    throw error
  }
}

/**
 * Get a specific email template by ID
 */
export async function getEmailTemplate(id: number): Promise<EmailTemplate> {
  try {
    return await api.get<EmailTemplate>(`/api/v1/email-templates/${id}`)
  } catch (error) {
    console.error('Failed to get email template:', error)
    throw error
  }
}

/**
 * Create a new email template
 */
export async function createEmailTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
  try {
    return await api.post<EmailTemplate>('/api/v1/email-templates', data)
  } catch (error) {
    console.error('Failed to create email template:', error)
    throw error
  }
}

/**
 * Update an email template
 */
export async function updateEmailTemplate(templateId: number, data: EmailTemplateUpdate): Promise<EmailTemplate> {
  try {
    return await api.patch<EmailTemplate>(`/api/v1/email-templates/${templateId}`, data)
  } catch (error) {
    console.error('Failed to update email template:', error)
    throw error
  }
}

/**
 * Delete an email template
 */
export async function deleteEmailTemplate(templateId: number): Promise<void> {
  try {
    await api.delete(`/api/v1/email-templates/${templateId}`)
  } catch (error) {
    console.error('Failed to delete email template:', error)
    throw error
  }
}

/**
 * Preview an email template with variable substitution
 */
export async function previewEmailTemplate(
  templateId: number,
  variables: Record<string, string>,
): Promise<{ subject: string; body_html: string }> {
  try {
    return await api.post<{ subject: string; body_html: string }>('/api/v1/email-templates/preview', {
      template_id: templateId,
      variables,
    })
  } catch (error) {
    console.error('Failed to preview email template:', error)
    throw error
  }
}
