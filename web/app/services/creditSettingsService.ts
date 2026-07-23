import type { CreditSettings } from '~/types'
import { ApiClient } from './api'

/**
 * Credit settings service for admin credit configuration management
 * @module services/creditSettingsService
 */

const CREDIT_SETTINGS_BASE_URL: string = '/api/v1/credit-settings'

export class CreditSettingsService {
  /**
   * Get current credit settings (public read access)
   * @returns Current credit settings
   * @throws If request fails
   */
  static async getCreditSettings(): Promise<CreditSettings> {
    return ApiClient.get<CreditSettings>(CREDIT_SETTINGS_BASE_URL)
  }

  /**
   * Update credit settings (admin only)
   * @param settingsData - Updated credit settings data
   * @returns Updated credit settings
   * @throws If request fails
   */
  static async updateCreditSettings(settingsData: Partial<CreditSettings>): Promise<CreditSettings> {
    return ApiClient.put<CreditSettings>(CREDIT_SETTINGS_BASE_URL, settingsData)
  }
}
