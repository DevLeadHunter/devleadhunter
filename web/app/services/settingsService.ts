/**
 * Settings service — HTTP client for user application settings.
 * @module services/settingsService
 */
import { api } from './api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Resend configuration as returned by the API.
 * Raw credentials are never exposed — only boolean flags indicate whether
 * they are stored.
 */
export interface ResendConfigResponse {
  /** Whether an API key is currently stored for this user. */
  has_api_key: boolean
  /** Whether a webhook secret is currently stored for this user. */
  has_webhook_secret: boolean
  /** Verified sender address (e.g. ``leo@mail.dibodev.fr``). */
  from_email: string | null
  /** Sender display name shown to recipients. */
  from_name: string | null
}

/**
 * Payload for creating or updating the Resend configuration.
 */
export interface ResendConfigUpdate {
  /** Resend API key (``re_…``). */
  api_key: string
  /** Resend webhook signing secret (``whsec_…``). Optional. */
  webhook_secret?: string
  /** Verified sender address. */
  from_email: string
  /** Sender display name. */
  from_name?: string
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/** HTTP client for the /settings API resource. */
export const settingsService = {
  /**
   * Fetch the current user's Resend configuration.
   *
   * @returns Configuration summary (no raw credentials).
   */
  async getResendConfig(): Promise<ResendConfigResponse> {
    return api.get<ResendConfigResponse>('/api/v1/settings/resend')
  },

  /**
   * Create or replace the current user's Resend configuration.
   * Credentials are encrypted server-side before being stored.
   *
   * @param data - New Resend configuration payload.
   * @returns Updated configuration summary.
   */
  async saveResendConfig(data: ResendConfigUpdate): Promise<ResendConfigResponse> {
    return api.put<ResendConfigResponse>('/api/v1/settings/resend', data)
  },
}
