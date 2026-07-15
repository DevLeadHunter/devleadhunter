import type { CreditSettings } from '~/types'
import { api } from './api'

/**
 * Credit settings service for admin credit configuration management
 * @module services/creditSettingsService
 */

const CREDIT_SETTINGS_BASE_URL = '/api/v1/credit-settings'

/**
 * Get current credit settings (public read access)
 * @returns {Promise<CreditSettings>} Current credit settings
 * @throws {Error} If request fails
 */
export async function getCreditSettings(): Promise<CreditSettings> {
  return api.get<CreditSettings>(CREDIT_SETTINGS_BASE_URL)
}

/**
 * Update credit settings (admin only)
 * @param {Partial<CreditSettings>} settingsData - Updated credit settings data
 * @returns {Promise<CreditSettings>} Updated credit settings
 * @throws {Error} If request fails
 */
export async function updateCreditSettings(settingsData: Partial<CreditSettings>): Promise<CreditSettings> {
  return api.put<CreditSettings>(CREDIT_SETTINGS_BASE_URL, settingsData)
}
