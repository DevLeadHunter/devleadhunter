import type { CreditTransaction } from '~/types'
import { api } from './api'

/**
 * Credit transaction service for managing credit transactions
 * @module services/creditTransactionService
 */

const CREDITS_BASE_URL = '/api/v1/credits'

/**
 * Get current user's credit transactions
 * @param {number} skip - Number of records to skip (pagination)
 * @param {number} limit - Maximum number of records to return
 * @returns {Promise<CreditTransaction[]>} List of credit transactions
 */
export async function getMyTransactions(skip: number = 0, limit: number = 100): Promise<CreditTransaction[]> {
  return api.get<CreditTransaction[]>(`${CREDITS_BASE_URL}/transactions?skip=${skip}&limit=${limit}`)
}

/**
 * Get current user's credit balance
 * @returns {Promise<{ user_id: number; balance: number; is_unlimited: boolean }>} Credit balance information
 */
export async function getMyBalance(): Promise<{
  user_id: number
  balance: number
  is_unlimited: boolean
}> {
  return api.get<{ user_id: number; balance: number; is_unlimited: boolean }>(`${CREDITS_BASE_URL}/balance`)
}
