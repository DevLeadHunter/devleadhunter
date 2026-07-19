/**
 * Email accounts service for managing email sender configurations.
 * @module services/emailAccountsService
 */

import type { EmailAccount } from '~/types'
import { api } from './api'

/**
 * Get all email accounts for the current user
 */
export async function getEmailAccounts(): Promise<EmailAccount[]> {
  try {
    return await api.get<EmailAccount[]>('/api/v1/email-accounts')
  } catch (error) {
    console.error('Failed to get email accounts:', error)
    throw error
  }
}

/**
 * Get Gmail OAuth authorization URL.
 * The browser is redirected here to Google's consent screen; Google then
 * returns to the backend callback which connects the account.
 */
export async function getGmailAuthUrl(): Promise<{ auth_url: string; instructions: string }> {
  try {
    return await api.post<{ auth_url: string; instructions: string }>('/api/v1/email-accounts/gmail/auth-url')
  } catch (error) {
    console.error('Failed to get Gmail auth URL:', error)
    throw error
  }
}

/**
 * Update an email account
 */
export async function updateEmailAccount(
  accountId: number,
  data: { name?: string; is_default?: boolean; is_active?: boolean },
): Promise<EmailAccount> {
  try {
    return await api.patch<EmailAccount>(`/api/v1/email-accounts/${accountId}`, data)
  } catch (error) {
    console.error('Failed to update email account:', error)
    throw error
  }
}

/**
 * Delete an email account
 */
export async function deleteEmailAccount(accountId: number): Promise<void> {
  try {
    await api.delete(`/api/v1/email-accounts/${accountId}`)
  } catch (error) {
    console.error('Failed to delete email account:', error)
    throw error
  }
}
