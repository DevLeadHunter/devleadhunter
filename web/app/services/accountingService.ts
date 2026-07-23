import type { AccountingResponse } from '~/types'
import { ApiClient } from './api'

/**
 * Accounting service for admin financial data
 * @module services/accountingService
 */

const ACCOUNTING_BASE_URL = '/api/v1/accounting'

export class AccountingService {
  /**
   * Get accounting data including transactions and summary
   * @param skip - Number of records to skip
   * @param limit - Maximum number of records to return
   * @returns Accounting data
   * @throws If request fails
   */
  static async getAccountingData(skip: number = 0, limit: number = 100): Promise<AccountingResponse> {
    return ApiClient.get<AccountingResponse>(`${ACCOUNTING_BASE_URL}?skip=${skip}&limit=${limit}`)
  }
}
