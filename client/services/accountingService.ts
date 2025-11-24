import type { AccountingResponse } from '~/types';
import { api } from './api';

/**
 * Accounting service for admin financial data
 * @module services/accountingService
 */

const ACCOUNTING_BASE_URL = '/api/v1/accounting';

/**
 * Get accounting data including transactions and summary
 * @param {number} skip - Number of records to skip
 * @param {number} limit - Maximum number of records to return
 * @returns {Promise<AccountingResponse>} Accounting data
 * @throws {Error} If request fails
 */
export async function getAccountingData(
  skip: number = 0,
  limit: number = 100
): Promise<AccountingResponse> {
  return api.get<AccountingResponse>(
    `${ACCOUNTING_BASE_URL}?skip=${skip}&limit=${limit}`
  );
}














