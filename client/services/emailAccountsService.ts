/**
 * Email accounts service for managing email sender configurations.
 * @module services/emailAccountsService
 */

import type {
  EmailAccount,
  EmailAccountCreateCustomDomain,
  EmailAccountCreateGmail,
  DNSVerificationResponse
} from '~/types';
import { api } from './api';

/**
 * Get all email accounts for the current user
 */
export async function getEmailAccounts(): Promise<EmailAccount[]> {
  try {
    return await api.get<EmailAccount[]>('/api/v1/email-accounts');
  } catch (error) {
    console.error('Failed to get email accounts:', error);
    throw error;
  }
}

/**
 * Get a specific email account by ID
 */
export async function getEmailAccount(id: number): Promise<EmailAccount> {
  try {
    return await api.get<EmailAccount>(`/api/v1/email-accounts/${id}`);
  } catch (error) {
    console.error('Failed to get email account:', error);
    throw error;
  }
}

/**
 * Create a custom domain email account
 */
export async function createCustomDomainAccount(
  data: EmailAccountCreateCustomDomain
): Promise<EmailAccount> {
  try {
    return await api.post<EmailAccount>(
      '/api/v1/email-accounts/custom-domain',
      data
    );
  } catch (error) {
    console.error('Failed to create custom domain account:', error);
    throw error;
  }
}

/**
 * Get Gmail OAuth authorization URL
 */
export async function getGmailAuthUrl(): Promise<{ auth_url: string; instructions: string }> {
  try {
    return await api.post<{ auth_url: string; instructions: string }>(
      '/api/v1/email-accounts/gmail/auth-url'
    );
  } catch (error) {
    console.error('Failed to get Gmail auth URL:', error);
    throw error;
  }
}

/**
 * Connect a Gmail account using OAuth code
 */
export async function connectGmailAccount(
  data: EmailAccountCreateGmail
): Promise<EmailAccount> {
  try {
    return await api.post<EmailAccount>(
      '/api/v1/email-accounts/gmail/connect',
      data
    );
  } catch (error) {
    console.error('Failed to connect Gmail account:', error);
    throw error;
  }
}

/**
 * Verify DNS records for a custom domain email account
 */
export async function verifyDnsRecords(accountId: number): Promise<DNSVerificationResponse> {
  try {
    return await api.post<DNSVerificationResponse>(
      `/api/v1/email-accounts/${accountId}/verify-dns`
    );
  } catch (error) {
    console.error('Failed to verify DNS records:', error);
    throw error;
  }
}

/**
 * Update an email account
 */
export async function updateEmailAccount(
  accountId: number,
  data: { name?: string; is_default?: boolean; is_active?: boolean }
): Promise<EmailAccount> {
  try {
    return await api.patch<EmailAccount>(
      `/api/v1/email-accounts/${accountId}`,
      data
    );
  } catch (error) {
    console.error('Failed to update email account:', error);
    throw error;
  }
}

/**
 * Delete an email account
 */
export async function deleteEmailAccount(accountId: number): Promise<void> {
  try {
    await api.delete(`/api/v1/email-accounts/${accountId}`);
  } catch (error) {
    console.error('Failed to delete email account:', error);
    throw error;
  }
}

