/**
 * Send policy service — the user's global cold-email cadence.
 * @module services/sendPolicyService
 */

import type { SendPolicy } from '~/types/Automation'
import { api } from './api'

const BASE_URL: string = '/api/v1/send-policy'

/**
 * Fetch the user's effective send policy (defaults when unset).
 * @returns The send policy.
 */
export async function getSendPolicy(): Promise<SendPolicy> {
  return api.get<SendPolicy>(BASE_URL)
}

/**
 * Create or update the user's send policy.
 * @param policy - The new policy values.
 * @returns The saved policy.
 */
export async function updateSendPolicy(policy: SendPolicy): Promise<SendPolicy> {
  return api.put<SendPolicy>(BASE_URL, policy)
}
