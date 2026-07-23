import type { CreditTransaction } from '~/types'
import { ApiClient } from './api'

/**
 * Credit transaction service for managing credit transactions
 * @module services/creditTransactionService
 */

const CREDITS_BASE_URL = '/api/v1/credits'

export class CreditTransactionService {
  /**
   * Get current user's credit transactions
   * @param skip - Number of records to skip (pagination)
   * @param limit - Maximum number of records to return
   * @returns List of credit transactions
   */
  static async getMyTransactions(skip: number = 0, limit: number = 100): Promise<CreditTransaction[]> {
    return ApiClient.get<CreditTransaction[]>(`${CREDITS_BASE_URL}/transactions?skip=${skip}&limit=${limit}`)
  }

  /**
   * Get current user's credit balance
   * @returns {Promise<{ user_id: number; balance: number; is_unlimited: boolean }>} Credit balance information
   */
  static async getMyBalance(): Promise<{
    user_id: number
    balance: number
    is_unlimited: boolean
  }> {
    return ApiClient.get<{ user_id: number; balance: number; is_unlimited: boolean }>(`${CREDITS_BASE_URL}/balance`)
  }
}
