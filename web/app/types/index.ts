/**
 * Shared TypeScript types and interfaces for the application
 */

/**
 * Business category for prospect search
 */
export type BusinessCategory = 'restaurant' | 'plombier' | 'electricien' | 'coiffeur' | 'garage' | 'all'

/**
 * Source of prospect data.
 *
 * Mirrors the backend ``Source`` enum in ``api/enums/source.py``.
 * - ``google``      — Google Maps / Google Business scraper
 * - ``pagesjaunes`` — Pages Jaunes directory scraper (Chrome / nodriver)
 * - ``yelp``        — Yelp platform scraper
 * - ``osm``         — OpenStreetMap / Overpass API (pure HTTP, fast)
 * - ``auto``        — Smart combo: OSM + Pages Jaunes in parallel, then email enrichment
 * - ``brightdata``  — BrightData HTTP API (Web Unlocker + SERP, no browser required)
 * - ``all``         — Sentinel value used in filter selects to mean "every source"
 */
export type ProspectSource = 'google' | 'pagesjaunes' | 'yelp' | 'osm' | 'auto' | 'brightdata' | 'manual' | 'all'

/**
 * Prospect interface representing a business without website
 */
export type Prospect = {
  id: number
  user_id: number
  name: string
  address?: string
  city?: string
  phone?: string
  email?: string
  website?: string
  category: string
  source: ProspectSource
  confidence: number
  contacted: boolean
  created_at?: string
  organization_id?: number | null
  reserved_by_user_id?: number | null
  reserved_by_name?: string | null
  reserved_at?: string | null
  lighthouse_json?: ProspectLighthouseAudit | null
  lighthouse_at?: string | null
}

/**
 * Résultat d'un audit Lighthouse (PageSpeed Insights) du site existant d'un prospect.
 */
export type ProspectLighthouseAudit = {
  scores: {
    performance: number | null
    accessibility: number | null
    bestPractices: number | null
    seo: number | null
  }
  is_improvable: boolean
  strategy: string
  final_url: string
  fetched_at: string
}

/**
 * Organisation (équipe) de l'utilisateur courant.
 */
export type Organization = {
  id: number
  name: string
  owner_user_id: number
  created_at?: string
  members: OrganizationMember[]
}

/**
 * Membre d'une organisation (identité résolue côté API).
 */
export type OrganizationMember = {
  user_id: number
  name: string
  email: string
  role: 'owner' | 'member'
  joined_at?: string
}

/**
 * Payload pour pré-remplir un prospect depuis Google Maps.
 */
export type ProspectEnrichPayload = {
  business_name?: string
  google_maps_url?: string
  city?: string
}

/**
 * Suggestion d'entreprise retournée par la recherche Google Maps.
 */
export type ProspectSearchSuggestion = {
  id: string
  label: string
  description?: string | null
  google_maps_url: string
}

/**
 * Payload pour rechercher des suggestions d'entreprises.
 */
export type ProspectSearchSuggestionsPayload = {
  query: string
  city?: string
  max_results?: number
}

/**
 * Payload pour mettre à jour un prospect existant (tous les champs sont optionnels).
 */
export type ProspectUpdatePayload = {
  name?: string
  address?: string | null
  city?: string | null
  phone?: string | null
  email?: string | null
  website?: string | null
  category?: string
  contacted?: boolean
}

/**
 * Payload pour créer un prospect manuellement.
 */
export type ProspectCreatePayload = {
  name: string
  address?: string | null
  city?: string | null
  phone?: string | null
  email?: string | null
  website?: string | null
  category: string
  source: ProspectSource
  confidence: number
}

/**
 * Formulaire de saisie pour l'ajout manuel d'un prospect.
 */
export type ManualProspectAddForm = {
  business_name: string
  google_maps_url: string
  city: string
}

/**
 * Search filters for prospect search
 */
export type ProspectSearchFilters = {
  category?: BusinessCategory
  city?: string
  source?: ProspectSource
  maxResults?: number
}

/**
 * Campaign interface for bulk email sending
 */
export type Campaign = {
  id: string
  name: string
  description: string
  prospectIds: string[]
  status: 'draft' | 'active' | 'completed'
  createdAt: string
  updatedAt: string
}

/**
 * User role enumeration
 */
export type UserRole = 'USER' | 'ADMIN'

/**
 * User interface
 */
export type User = {
  id: number
  name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string | null
  credit_balance?: number | null
  credits_available?: number | null
  credits_consumed?: number | null
  onboarding_completed?: boolean
}

/**
 * Login credentials
 */
export type LoginCredentials = {
  email: string
  password: string
}

/**
 * Signup data
 */
export type SignupData = {
  name: string
  email: string
  password: string
}

/**
 * Profile update payload (self-service `PATCH /auth/me`) — fields are optional so
 * the user can change name and/or email.
 */
export type ProfileUpdate = {
  name?: string
  email?: string
}

/**
 * API Response wrapper
 */
export type ApiResponse<T> = {
  data: T
  success: boolean
  message?: string
}

/**
 * Auth token response
 */
export type TokenResponse = {
  access_token: string
  token_type: string
}

/**
 * Paginated response
 */
export type PaginatedResponse<T> = {
  items: T[]
  total: number
  page: number
  perPage: number
  totalPages: number
}

/**
 * Credit settings interface for credit system configuration
 */
export type CreditSettings = {
  id: number
  price_per_credit: number
  credits_per_search: number
  credits_per_result: number
  credits_per_email: number
  free_credits_on_signup: number
  minimum_credits_purchase: number
  created_at: string
  updated_at: string | null
}

/**
 * Checkout session creation request
 */
export type CheckoutSessionCreate = {
  credits: number
  success_url?: string
  cancel_url?: string
}

/**
 * Checkout session response
 */
export type CheckoutSessionResponse = {
  session_id: string
  url: string
  amount: number
  credits: number
}

/**
 * Credit transaction type
 */
export type CreditTransactionType = 'PURCHASE' | 'USAGE' | 'REFUND' | 'FREE_GIFT'

/**
 * Credit transaction interface
 */
export type CreditTransaction = {
  id: number
  user_id: number
  transaction_type: CreditTransactionType
  amount: number
  description: string
  transaction_metadata?: string | null
  created_at: string
}

/**
 * Credit balance response
 */
export type CreditBalanceResponse = {
  user_id: number
  balance: number
  is_unlimited: boolean
}

/**
 * Stripe payment information
 */
export type StripePaymentInfo = {
  payment_intent_id?: string | null
  session_id?: string | null
  amount: number
  currency: string
  status: string
  payment_method_type?: string | null
  payment_method_brand?: string | null
  payment_method_last4?: string | null
  payment_date: string
  amount_received?: number | null
  application_fee_amount?: number | null
  net_amount?: number | null
  available_at?: string | null
  refund_amount?: number | null
  refund_date?: string | null
  customer_country?: string | null
  customer_email?: string | null
  ip_address?: string | null
  user_agent?: string | null
}

/**
 * Credit purchase transaction with payment details
 */
export type CreditPurchaseTransaction = {
  transaction_id: number
  user_id: number
  user_name: string
  user_email: string
  credits_amount: number
  credits_available_date: string
  payment_info?: StripePaymentInfo | null
  euros_amount?: number | null
  description: string
}

/**
 * Accounting summary
 */
export type AccountingSummary = {
  total_paid: number
  total_refunded: number
  total_stripe_fees: number
  net_total: number
  total_transactions: number
  available_balance?: number | null
}

/**
 * Accounting data response
 */
export type AccountingResponse = {
  summary: AccountingSummary
  transactions: CreditPurchaseTransaction[]
}

/**
 * Support ticket status values
 */
export type SupportTicketStatus = 'open' | 'waiting_user' | 'waiting_support' | 'resolved' | 'closed'

/**
 * Support ticket topics
 */
export type SupportTicketTopic =
  | 'credits_billing'
  | 'missing_results'
  | 'bug_report'
  | 'refund_credits'
  | 'refund_payment'
  | 'feature_request'
  | 'other'

/**
 * Support topic metadata for UI
 */
export type SupportTopicOption = {
  value: SupportTicketTopic
  label: string
  description: string
}

/**
 * Support attachment metadata
 */
export type SupportAttachment = {
  id: number
  url: string
  original_filename: string
  content_type: string
  created_at: string
}

/**
 * Support message
 */
export type SupportMessage = {
  id: number
  ticket_id: number
  sender_id: number
  sender_name: string
  sender_role: UserRole
  content: string
  attachments: SupportAttachment[]
  created_at: string
}

/**
 * Support ticket summary
 */
export type SupportTicketSummary = {
  id: number
  user_id: number
  user_name: string
  topic: SupportTicketTopic
  subject: string
  description: string
  status: SupportTicketStatus
  created_at: string
  updated_at?: string | null
  last_message_at?: string | null
  closed_at?: string | null
  messages_count: number
  attachments_count: number
}

/**
 * Detailed support ticket with conversation
 */
export interface SupportTicketDetail extends Omit<SupportTicketSummary, 'messages_count'> {
  attachments: SupportAttachment[]
  messages: SupportMessage[]
}

/**
 * Email account type
 */
export type EmailAccountType = 'custom_domain' | 'gmail_oauth' | 'resend'

/**
 * Email account interface
 */
export type EmailAccount = {
  id: number
  user_id: number
  account_type: EmailAccountType
  email: string
  name: string
  is_verified: boolean
  is_default: boolean
  is_active: boolean
  domain?: string | null
  spf_verified: boolean
  dkim_verified: boolean
  oauth_token_expires_at?: string | null
  created_at: string
  updated_at?: string | null
}

/**
 * Email template interface
 */
export type EmailTemplate = {
  id: number
  user_id: number
  email_account_id?: number | null
  name: string
  subject: string
  body_html: string
  variables?: string[]
  signature_id?: number | null
  is_active: boolean
  created_at: string
  updated_at?: string | null
}

/**
 * Reusable email signature (sign-off block, HTML, paste-friendly from Gmail).
 */
export type EmailSignature = {
  id: number
  user_id: number
  name: string
  content_html: string
  is_default: boolean
  created_at: string
  updated_at?: string | null
}

/**
 * Email signature creation request
 */
export type EmailSignatureCreate = {
  name: string
  content_html: string
  is_default?: boolean
}

/**
 * Email signature update request
 */
export type EmailSignatureUpdate = {
  name?: string
  content_html?: string
  is_default?: boolean
}

/**
 * Email status
 */
export type EmailStatus =
  | 'pending'
  | 'sending'
  | 'scheduled'
  | 'sent'
  | 'delivered'
  | 'delivery_delayed'
  | 'opened'
  | 'clicked'
  | 'bounced'
  | 'failed'
  | 'complained'
  | 'suppressed'

/**
 * A follow-up step in a campaign email sequence.
 */
export type CampaignFollowUp = {
  id: number
  campaign_id: number
  template_id: number
  template_name?: string | null
  template_subject?: string | null
  delay_days: number
  position: number
  created_at: string
}

/**
 * A/B stats for one variant.
 */
export type CampaignVariantStats = {
  variant: 'A' | 'B'
  sent: number
  delivered: number
  opened: number
  clicked: number
  open_rate: number
  click_rate: number
}

/**
 * Email log interface
 */
export type EmailLog = {
  id: number
  user_id: number
  email_account_id: number | null
  prospect_id?: string | null
  campaign_id?: string | null
  recipient_email: string
  recipient_name?: string | null
  subject: string
  body_html?: string | null
  status: EmailStatus
  provider: string
  provider_message_id?: string | null
  sent_at?: string | null
  delivered_at?: string | null
  opened_at?: string | null
  clicked_at?: string | null
  bounced_at?: string | null
  complained_at?: string | null
  suppressed_at?: string | null
  failed_at?: string | null
  ab_variant?: string | null
  error_message?: string | null
  created_at: string
  updated_at?: string | null
}

/**
 * Email account creation request (custom domain)
 */
export type EmailAccountCreateCustomDomain = {
  email: string
  name: string
  domain: string
  is_default?: boolean
}

/**
 * Email account creation request (Gmail OAuth)
 */
export type EmailAccountCreateGmail = {
  email: string
  name: string
  oauth_code: string
  is_default?: boolean
}

/**
 * Email template creation request
 */
export type EmailTemplateCreate = {
  name: string
  subject: string
  body_html: string
  email_account_id?: number
  variables?: string[]
  signature_id?: number | null
}

/**
 * Email template update request
 */
export type EmailTemplateUpdate = {
  name?: string
  subject?: string
  body_html?: string
  email_account_id?: number
  variables?: string[]
  is_active?: boolean
  signature_id?: number | null
}

/**
 * Send email request
 */
export type SendEmailRequest = {
  email_account_id: number
  recipient_email: string
  recipient_name?: string
  subject: string
  body_html: string
  prospect_id?: string
  template_id?: number
  variables?: Record<string, string>
}

/**
 * Send campaign email request
 */
export type SendCampaignEmailRequest = {
  email_account_id: number
  campaign_id: string
  template_id: number
  prospect_ids: string[]
  variables_per_prospect?: Record<string, Record<string, string>>
}

/**
 * Email stats response
 */
export type EmailStats = {
  total_sent: number
  total_delivered: number
  total_opened: number
  total_clicked: number
  total_bounced: number
  total_failed: number
  delivery_rate: number
  open_rate: number
  click_rate: number
}

/**
 * DNS verification response
 */
export type DNSVerificationResponse = {
  spf_verified: boolean
  dkim_verified: boolean
  is_verified: boolean
  spf_record?: string | null
  dkim_record?: string | null
  instructions: string
}
