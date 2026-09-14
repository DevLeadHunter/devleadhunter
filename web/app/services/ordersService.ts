import { ApiClient } from './api'

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
  billing_address: string | null
  billing_city: string | null
  billing_zip_code: string | null
  billing_country_code: string | null
  billing_tax_id: string | null
  billing_vat_number: string | null
  stripe_payment_url: string | null
  payment_provider: string | null
  payment_url: string | null
  invoice_id: string | null
  invoice_number: string | null
  domain: string | null
  notes: string | null
  /** OVH order behind the go-live domain purchase (raw status, labelled by the drawer). */
  ovh_order_id: number | null
  ovh_order_status: string | null
  payment_link_sent_at: string | null
  paid_at: string | null
  delivered_at: string | null
  created_at: string
  updated_at: string | null
  /** Follow-up warning shown in the drawer (e.g. site live but CMS not handed over). */
  delivery_warning?: string | null
}

/** Billing counterpart of the invoice, reviewed before it is issued. */
export type OrderBillingDetails = {
  name: string | null
  email: string | null
  address: string | null
  city: string | null
  zip_code: string | null
  country_code: string
  tax_id: string | null
  vat_number: string | null
}

/** Billing details pre-filled by the API, with the provider and fields still required. */
export type OrderBillingPrefill = OrderBillingDetails & {
  invoicing_provider: string | null
  missing_fields: string[]
}

/** Result of reconciling an order against its payment provider. */
export type OrderPaymentCheckResult = {
  newly_paid: boolean
  order: Order
}

/** Paginated list of orders. */
export type OrderListResponse = {
  items: Order[]
  total: number
}

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

export class OrdersService {
  /**
   * List the current user's orders.
   * @returns The order list response.
   */
  static async listOrders(): Promise<OrderListResponse> {
    return ApiClient.get<OrderListResponse>('/api/v1/orders')
  }

  /**
   * Fetch commercial KPIs for the current user.
   * @returns Aggregated sales stats.
   */
  static async getOrderStats(): Promise<OrderStats> {
    return ApiClient.get<OrderStats>('/api/v1/orders/stats')
  }

  /**
   * Create a manual order.
   * @param payload - Order creation fields.
   * @returns The created order.
   */
  static async createOrder(payload: OrderCreatePayload): Promise<Order> {
    return ApiClient.post<Order>('/api/v1/orders', payload)
  }

  /**
   * Update an order's editable fields.
   * @param orderId - Target order id.
   * @param payload - Fields to update.
   * @returns The updated order.
   */
  static async updateOrder(orderId: number, payload: OrderUpdatePayload): Promise<Order> {
    return ApiClient.patch<Order>(`/api/v1/orders/${orderId}`, payload)
  }

  /**
   * Delete (cancel) an order.
   * @param orderId - Target order id.
   */
  static async deleteOrder(orderId: number): Promise<void> {
    await ApiClient.delete<unknown>(`/api/v1/orders/${orderId}`)
  }

  /**
   * Generate (or refresh) the Stripe payment link for an order.
   * @param orderId - Target order id.
   * @returns The order with its payment URL set.
   */
  static async createOrderPaymentLink(orderId: number): Promise<Order> {
    return ApiClient.post<Order>(`/api/v1/orders/${orderId}/payment-link`, {})
  }

  /**
   * Fetch the invoice's billing details, pre-filled from the prospect when unset.
   * @param orderId - Target order id.
   * @returns The billing details and the fields still required.
   */
  static async getOrderBilling(orderId: number): Promise<OrderBillingPrefill> {
    return ApiClient.get<OrderBillingPrefill>(`/api/v1/orders/${orderId}/billing`)
  }

  /**
   * Issue the invoice at the user's provider from the reviewed billing details.
   * @param orderId - Target order id.
   * @param billing - The reviewed billing counterpart.
   * @param amountCents - The negotiated amount, in cents.
   * @returns The order carrying its issued invoice.
   */
  static async finalizeOrder(orderId: number, billing: OrderBillingDetails, amountCents: number): Promise<Order> {
    return ApiClient.post<Order>(`/api/v1/orders/${orderId}/finalize`, { billing, amount_cents: amountCents })
  }

  /**
   * Render the payment-link email for review before sending.
   * @param orderId - Target order id.
   * @returns The rendered subject and HTML body.
   */
  static async previewOrderPaymentEmail(orderId: number): Promise<OrderPaymentEmailPreview> {
    return ApiClient.get<OrderPaymentEmailPreview>(`/api/v1/orders/${orderId}/payment-email/preview`)
  }

  /**
   * Send the payment-link email to the client.
   * @param orderId - Target order id.
   * @returns The updated order.
   */
  static async sendOrderPaymentEmail(orderId: number): Promise<Order> {
    return ApiClient.post<Order>(`/api/v1/orders/${orderId}/payment-email/send`, {})
  }

  /**
   * Manually mark an order as paid.
   * @param orderId - Target order id.
   * @returns The updated order.
   */
  static async markOrderPaid(orderId: number): Promise<Order> {
    return ApiClient.post<Order>(`/api/v1/orders/${orderId}/mark-paid`, {})
  }

  /**
   * Reconcile an order against its provider, marking it paid if the invoice is.
   * @param orderId - Target order id.
   * @returns Whether this call marked it paid, and the refreshed order.
   */
  static async checkOrderPayment(orderId: number): Promise<OrderPaymentCheckResult> {
    return ApiClient.post<OrderPaymentCheckResult>(`/api/v1/orders/${orderId}/check-payment`, {})
  }

  /**
   * Put the sold site online (Vercel + domain) and hand over CMS access.
   * @param orderId - Target order id.
   * @returns The updated order.
   */
  static async deployOrder(orderId: number): Promise<Order> {
    return ApiClient.post<Order>(`/api/v1/orders/${orderId}/deploy`, {})
  }

  /**
   * Refund a paid order through its provider and mark it refunded.
   * @param orderId - Target order id.
   * @returns The updated order.
   */
  static async refundOrder(orderId: number): Promise<Order> {
    return ApiClient.post<Order>(`/api/v1/orders/${orderId}/refund`, {})
  }
}
