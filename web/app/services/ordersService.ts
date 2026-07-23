import { api } from './api'

/** A commercial order (sale of a product to a client). */
export type Order = {
  id: number
  product_type: string
  status: string
  prospect_id: number | null
  demo_site_id: number | null
  amount_cents: number
  currency: string
  business_name: string | null
  customer_name: string | null
  customer_email: string | null
  stripe_payment_url: string | null
  domain: string | null
  notes: string | null
  payment_link_sent_at: string | null
  paid_at: string | null
  delivered_at: string | null
  created_at: string
  updated_at: string | null
}

/** Paginated list of orders. */
export type OrderListResponse = {
  items: Order[]
  total: number
}

/** Payload to create a manual order. */
export type OrderCreatePayload = {
  product_type?: string
  prospect_id?: number | null
  demo_site_id?: number | null
  amount_cents?: number | null
  business_name?: string | null
  customer_name?: string | null
  customer_email?: string | null
  domain?: string | null
  notes?: string | null
}

/** Partial update of an order. */
export type OrderUpdatePayload = Partial<OrderCreatePayload> & { status?: string }

/** Rendered payment-link email preview. */
export type OrderPaymentEmailPreview = {
  subject: string
  body_html: string
}

/** Commercial KPIs for the current user. */
export type OrderStats = {
  total_orders: number
  won_count: number
  pending_count: number
  revenue_cents: number
  pipeline_cents: number
  currency: string
}

/**
 * List the current user's orders.
 * @returns The order list response.
 */
export async function listOrders(): Promise<OrderListResponse> {
  return api.get<OrderListResponse>('/api/v1/orders')
}

/**
 * Fetch commercial KPIs for the current user.
 * @returns Aggregated sales stats.
 */
export async function getOrderStats(): Promise<OrderStats> {
  return api.get<OrderStats>('/api/v1/orders/stats')
}

/**
 * Create a manual order.
 * @param payload - Order creation fields.
 * @returns The created order.
 */
export async function createOrder(payload: OrderCreatePayload): Promise<Order> {
  return api.post<Order>('/api/v1/orders', payload)
}

/**
 * Update an order's editable fields.
 * @param orderId - Target order id.
 * @param payload - Fields to update.
 * @returns The updated order.
 */
export async function updateOrder(orderId: number, payload: OrderUpdatePayload): Promise<Order> {
  return api.patch<Order>(`/api/v1/orders/${orderId}`, payload)
}

/**
 * Delete (cancel) an order.
 * @param orderId - Target order id.
 */
export async function deleteOrder(orderId: number): Promise<void> {
  await api.delete<unknown>(`/api/v1/orders/${orderId}`)
}

/**
 * Generate (or refresh) the Stripe payment link for an order.
 * @param orderId - Target order id.
 * @returns The order with its payment URL set.
 */
export async function createOrderPaymentLink(orderId: number): Promise<Order> {
  return api.post<Order>(`/api/v1/orders/${orderId}/payment-link`, {})
}

/**
 * Render the payment-link email for review before sending.
 * @param orderId - Target order id.
 * @returns The rendered subject and HTML body.
 */
export async function previewOrderPaymentEmail(orderId: number): Promise<OrderPaymentEmailPreview> {
  return api.get<OrderPaymentEmailPreview>(`/api/v1/orders/${orderId}/payment-email/preview`)
}

/**
 * Send the payment-link email to the client.
 * @param orderId - Target order id.
 * @returns The updated order.
 */
export async function sendOrderPaymentEmail(orderId: number): Promise<Order> {
  return api.post<Order>(`/api/v1/orders/${orderId}/payment-email/send`, {})
}

/**
 * Manually mark an order as paid.
 * @param orderId - Target order id.
 * @returns The updated order.
 */
export async function markOrderPaid(orderId: number): Promise<Order> {
  return api.post<Order>(`/api/v1/orders/${orderId}/mark-paid`, {})
}

/**
 * Put the sold site online (Vercel + domain) and hand over CMS access.
 * @param orderId - Target order id.
 * @returns The updated order.
 */
export async function deployOrder(orderId: number): Promise<Order> {
  return api.post<Order>(`/api/v1/orders/${orderId}/deploy`, {})
}
