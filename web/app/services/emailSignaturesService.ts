/**
 * Email signatures service — CRUD for a user's reusable email signatures.
 * @module services/emailSignaturesService
 */

import type { EmailSignature, EmailSignatureCreate, EmailSignatureUpdate } from '~/types'
import { api } from './api'

/**
 * Get every signature of the current user (default first, then newest).
 * @returns The user's signatures.
 */
export async function getEmailSignatures(): Promise<EmailSignature[]> {
  try {
    return await api.get<EmailSignature[]>('/api/v1/email-signatures')
  } catch (error) {
    console.error('Failed to get email signatures:', error)
    throw error
  }
}

/**
 * Create a new signature.
 * @param data - Signature payload.
 * @returns The created signature.
 */
export async function createEmailSignature(data: EmailSignatureCreate): Promise<EmailSignature> {
  try {
    return await api.post<EmailSignature>('/api/v1/email-signatures', data)
  } catch (error) {
    console.error('Failed to create email signature:', error)
    throw error
  }
}

/**
 * Update a signature.
 * @param signatureId - Signature to update.
 * @param data - Partial signature payload.
 * @returns The updated signature.
 */
export async function updateEmailSignature(signatureId: number, data: EmailSignatureUpdate): Promise<EmailSignature> {
  try {
    return await api.patch<EmailSignature>(`/api/v1/email-signatures/${signatureId}`, data)
  } catch (error) {
    console.error('Failed to update email signature:', error)
    throw error
  }
}

/**
 * Delete a signature.
 * @param signatureId - Signature to delete.
 * @returns A promise that resolves once removed.
 */
export async function deleteEmailSignature(signatureId: number): Promise<void> {
  try {
    await api.delete(`/api/v1/email-signatures/${signatureId}`)
  } catch (error) {
    console.error('Failed to delete email signature:', error)
    throw error
  }
}
