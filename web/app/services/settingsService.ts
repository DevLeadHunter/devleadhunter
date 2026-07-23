/**
 * Settings service — HTTP client for user application settings.
 * @module services/settingsService
 */
import { ApiClient } from './api'

/**
 * Resend configuration as returned by the API.
 * Raw credentials are never exposed — only boolean flags indicate whether
 * they are stored.
 */
export type ResendConfigResponse = {
  has_api_key: boolean
  has_webhook_secret: boolean
  from_email: string | null
  from_name: string | null
}

/**
 * Payload for creating or updating the Resend configuration.
 */
export type ResendConfigUpdate = {
  api_key: string
  webhook_secret?: string
  from_email: string
  from_name?: string
}

/** The active email-sending transport for the user. */
export type SendingProvider = 'resend' | 'gmail'

/**
 * Summary of the user's sending setup (no secrets): the active provider plus
 * a readiness flag for each provider.
 */
export type SendingIdentityResponse = {
  provider: SendingProvider
  resend_configured: boolean
  resend_from_email: string | null
  gmail_configured: boolean
  gmail_email: string | null
}

/** HTTP client for the /settings API resource. */
export class SettingsService {
  /**
   * Fetch the current user's Resend configuration.
   *
   * @returns Configuration summary (no raw credentials).
   */
  static async getResendConfig(): Promise<ResendConfigResponse> {
    return ApiClient.get<ResendConfigResponse>('/api/v1/settings/resend')
  }

  /**
   * Create or replace the current user's Resend configuration.
   * Credentials are encrypted server-side before being stored.
   *
   * @param data - New Resend configuration payload.
   * @returns Updated configuration summary.
   */
  static async saveResendConfig(data: ResendConfigUpdate): Promise<ResendConfigResponse> {
    return ApiClient.put<ResendConfigResponse>('/api/v1/settings/resend', data)
  }

  /**
   * Fetch the user's active sending provider and each provider's readiness.
   *
   * @returns Sending-identity summary (no secrets).
   */
  static async getSendingIdentity(): Promise<SendingIdentityResponse> {
    return ApiClient.get<SendingIdentityResponse>('/api/v1/settings/sending-identity')
  }

  /**
   * Switch the user's active sending provider.
   * Rejected (422) by the API when the target provider is not configured yet.
   *
   * @param provider - Target transport (``resend`` | ``gmail``).
   * @returns Updated sending-identity summary.
   */
  static async setSendingProvider(provider: SendingProvider): Promise<SendingIdentityResponse> {
    return ApiClient.put<SendingIdentityResponse>('/api/v1/settings/sending-identity', { provider })
  }
}
