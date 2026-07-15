import type { CheckoutSessionCreate, CheckoutSessionResponse } from '~/types'
import { api } from './api'

/**
 * Payment service for Stripe checkout sessions
 * @module services/paymentService
 */

const PAYMENTS_BASE_URL = '/api/v1/payments'

/**
 * Create a Stripe checkout session
 * @param {CheckoutSessionCreate} data - Checkout session creation data
 * @returns {Promise<CheckoutSessionResponse>} Checkout session response with URL
 * @throws {Error} If request fails
 */
export async function createCheckoutSession(data: CheckoutSessionCreate): Promise<CheckoutSessionResponse> {
  return api.post<CheckoutSessionResponse>(`${PAYMENTS_BASE_URL}/create-checkout-session`, data)
}

/**
 * Get Stripe public key
 * @returns {Promise<{ public_key: string }>} Stripe public key
 * @throws {Error} If request fails
 */
export async function getStripePublicKey(): Promise<{ public_key: string }> {
  return api.get<{ public_key: string }>(`${PAYMENTS_BASE_URL}/public-key`)
}

/**
 * Verify a Stripe checkout session and ensure credits are added
 * @param {string} sessionId - Stripe checkout session ID
 * @returns {Promise<{ status: string; message: string; paid: boolean; credits_added?: number }>} Verification result
 * @throws {Error} If request fails
 */
export async function verifyCheckoutSession(
  sessionId: string,
): Promise<{ status: string; message: string; paid: boolean; credits_added?: number }> {
  return api.post<{ status: string; message: string; paid: boolean; credits_added?: number }>(
    `${PAYMENTS_BASE_URL}/verify-session/${sessionId}`,
  )
}
