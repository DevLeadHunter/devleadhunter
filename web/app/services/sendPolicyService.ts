/**
 * Send policy service — the user's global cold-email cadence.
 * @module services/sendPolicyService
 */

import type { SendPolicy } from '~/types/Automation'
import { ApiClient } from './api'

const BASE_URL: string = '/api/v1/send-policy'

export class SendPolicyService {
  /**
   * Fetch the user's effective send policy (defaults when unset).
   * @returns The send policy.
   */
  static async getSendPolicy(): Promise<SendPolicy> {
    return ApiClient.get<SendPolicy>(BASE_URL)
  }

  /**
   * Create or update the user's send policy.
   * @param policy - The new policy values.
   * @returns The saved policy.
   */
  static async updateSendPolicy(policy: SendPolicy): Promise<SendPolicy> {
    return ApiClient.put<SendPolicy>(BASE_URL, policy)
  }
}
