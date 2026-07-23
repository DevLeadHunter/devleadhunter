import type { CheckoutSessionCreate, CheckoutSessionResponse } from '~/types'
import { ApiClient } from './api'

/**
 * Payment service for Stripe checkout sessions
 * @module services/paymentService
 */

const PAYMENTS_BASE_URL: string = '/api/v1/payments'

export class PaymentService {
  /**
   * Create a Stripe checkout session
   * @param data - Checkout session creation data
   * @returns Checkout session response with URL
   * @throws If request fails
   */
  static async createCheckoutSession(data: CheckoutSessionCreate): Promise<CheckoutSessionResponse> {
    return ApiClient.post<CheckoutSessionResponse>(`${PAYMENTS_BASE_URL}/create-checkout-session`, data)
  }

  /**
   * Get Stripe public key
   * @returns {Promise<{ public_key: string }>} Stripe public key
   * @throws If request fails
   */
  static async getStripePublicKey(): Promise<{ public_key: string }> {
    return ApiClient.get<{ public_key: string }>(`${PAYMENTS_BASE_URL}/public-key`)
  }

  /**
   * Verify a Stripe checkout session and ensure credits are added
   * @param sessionId - Stripe checkout session ID
   * @returns {Promise<{ status: string; message: string; paid: boolean; credits_added?: number }>} Verification result
   * @throws If request fails
   */
  static async verifyCheckoutSession(
    sessionId: string,
  ): Promise<{ status: string; message: string; paid: boolean; credits_added?: number }> {
    return ApiClient.post<{ status: string; message: string; paid: boolean; credits_added?: number }>(
      `${PAYMENTS_BASE_URL}/verify-session/${sessionId}`,
      {},
    )
  }
}
