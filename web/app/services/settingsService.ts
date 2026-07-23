/**
 * Settings service — HTTP client for user application settings.
 * @module services/settingsService
 */
import { ApiClient } from './api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Resend configuration as returned by the API.
 * Raw credentials are never exposed — only boolean flags indicate whether
 * they are stored.
 */
export type ResendConfigResponse = {
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
export type ResendConfigUpdate = {
  /** Resend API key (``re_…``). */
  api_key: string
  /** Resend webhook signing secret (``whsec_…``). Optional. */
  webhook_secret?: string
  /** Verified sender address. */
  from_email: string
  /** Sender display name. */
  from_name?: string
}

/** The active email-sending transport for the user. */
export type SendingProvider = 'resend' | 'gmail'

/**
 * Summary of the user's sending setup (no secrets): the active provider plus
 * a readiness flag for each provider.
 */
export type SendingIdentityResponse = {
  /** Currently active transport (``resend`` | ``gmail``). */
  provider: SendingProvider
  /** Whether the Resend config (API key + from address) is usable. */
  resend_configured: boolean
  /** Verified Resend sender address, when configured. */
  resend_from_email: string | null
  /** Whether a Gmail account is connected and usable. */
  gmail_configured: boolean
  /** Connected Gmail address, when present. */
  gmail_email: string | null
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

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
