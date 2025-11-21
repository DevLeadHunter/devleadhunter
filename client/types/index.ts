/**
 * Shared TypeScript types and interfaces for the application
 * @module types
 */

/**
 * Business category for prospect search
 */
export type BusinessCategory = 
  | 'restaurant' 
  | 'plombier' 
  | 'electricien' 
  | 'coiffeur' 
  | 'garage' 
  | 'all';

/**
 * Source of prospect data
 */
export type ProspectSource = 
  | 'google' 
  | 'pagesjaunes' 
  | 'yelp' 
  | 'osm' 
  | 'mappy'
  | 'mock'
  | 'all';

/**
 * Prospect interface representing a business without website
 */
export interface Prospect {
  /** Unique identifier for the prospect */
  id: number;
  /** User ID who saved this prospect */
  user_id: number;
  /** Business name */
  name: string;
  /** Street address */
  address?: string;
  /** City */
  city?: string;
  /** Phone number */
  phone?: string;
  /** Email address (if available) */
  email?: string;
  /** Website URL (if available) */
  website?: string;
  /** Business category */
  category: string;
  /** Source of the prospect data */
  source: ProspectSource;
  /** Confidence score (1-4) */
  confidence: number;
  /** Timestamp of when prospect was found */
  created_at?: string;
}

/**
 * Search filters for prospect search
 */
export interface ProspectSearchFilters {
  /** Business category filter */
  category?: BusinessCategory;
  /** City filter */
  city?: string;
  /** Source filter */
  source?: ProspectSource;
  /** Maximum number of results */
  maxResults?: number;
}

/**
 * Campaign interface for bulk email sending
 */
export interface Campaign {
  /** Unique identifier for the campaign */
  id: string;
  /** Campaign name */
  name: string;
  /** Campaign description */
  description: string;
  /** List of prospect IDs in the campaign */
  prospectIds: string[];
  /** Campaign status */
  status: 'draft' | 'active' | 'completed';
  /** Timestamp of creation */
  createdAt: string;
  /** Timestamp of last update */
  updatedAt: string;
}

/**
 * User role enumeration
 */
export type UserRole = 'USER' | 'ADMIN';

/**
 * User interface
 */
export interface User {
  /** Unique identifier for the user */
  id: number;
  /** User name */
  name: string;
  /** User email */
  email: string;
  /** User role */
  role: UserRole;
  /** Whether user is active */
  is_active: boolean;
  /** Timestamp of account creation */
  created_at: string;
  /** Timestamp of last update */
  updated_at: string | null;
  /** Credit balance (-1 for unlimited/admin) */
  credit_balance?: number | null;
  /** Credits available (-1 for unlimited/admin) */
  credits_available?: number | null;
  /** Credits consumed */
  credits_consumed?: number | null;
}

/**
 * Login credentials
 */
export interface LoginCredentials {
  /** User email */
  email: string;
  /** User password */
  password: string;
}

/**
 * Signup data
 */
export interface SignupData {
  /** User name */
  name: string;
  /** User email */
  email: string;
  /** User password */
  password: string;
}

/**
 * API Response wrapper
 */
export interface ApiResponse<T> {
  /** Response data */
  data: T;
  /** Success status */
  success: boolean;
  /** Error message (if any) */
  message?: string;
}

/**
 * Auth token response
 */
export interface TokenResponse {
  /** JWT access token */
  access_token: string;
  /** Token type */
  token_type: string;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  /** List of items */
  items: T[];
  /** Total number of items */
  total: number;
  /** Current page */
  page: number;
  /** Items per page */
  perPage: number;
  /** Total number of pages */
  totalPages: number;
}

/**
 * Email sending data
 */
export interface EmailData {
  /** Recipient email */
  to: string;
  /** Email subject */
  subject: string;
  /** Email body */
  body: string;
  /** Prospect ID (optional) */
  prospectId?: string;
}

/**
 * Bulk email sending data
 */
export interface BulkEmailData {
  /** Campaign ID */
  campaignId: string;
  /** Email subject */
  subject: string;
  /** Email body */
  body: string;
}

/**
 * Credit settings interface for credit system configuration
 */
export interface CreditSettings {
  /** Unique identifier for the settings (always 1) */
  id: number;
  /** Price of one credit in EUR */
  price_per_credit: number;
  /** Number of credits required for a search operation */
  credits_per_search: number;
  /** Number of credits required per prospect found */
  credits_per_result: number;
  /** Number of credits required per email sent */
  credits_per_email: number;
  /** Number of free credits given on user registration */
  free_credits_on_signup: number;
  /** Minimum number of credits that can be purchased */
  minimum_credits_purchase: number;
  /** Timestamp when settings were created */
  created_at: string;
  /** Timestamp when settings were last updated */
  updated_at: string | null;
}

/**
 * Checkout session creation request
 */
export interface CheckoutSessionCreate {
  /** Number of credits to purchase */
  credits: number;
  /** URL to redirect after successful payment (optional) */
  success_url?: string;
  /** URL to redirect if payment is cancelled (optional) */
  cancel_url?: string;
}

/**
 * Checkout session response
 */
export interface CheckoutSessionResponse {
  /** Stripe checkout session ID */
  session_id: string;
  /** Stripe checkout session URL */
  url: string;
  /** Payment amount in cents */
  amount: number;
  /** Number of credits being purchased */
  credits: number;
}

/**
 * Credit transaction type
 */
export type CreditTransactionType = 'PURCHASE' | 'USAGE' | 'REFUND' | 'FREE_GIFT';

/**
 * Credit transaction interface
 */
export interface CreditTransaction {
  /** Transaction unique identifier */
  id: number;
  /** User ID who owns this transaction */
  user_id: number;
  /** Transaction type */
  transaction_type: CreditTransactionType;
  /** Number of credits (positive for additions, negative for usage) */
  amount: number;
  /** Description of the transaction */
  description: string;
  /** Optional JSON metadata */
  transaction_metadata?: string | null;
  /** Timestamp when transaction was created */
  created_at: string;
}

/**
 * Credit balance response
 */
export interface CreditBalanceResponse {
  /** User ID */
  user_id: number;
  /** Current credit balance */
  balance: number;
  /** Whether user has unlimited credits (admin) */
  is_unlimited: boolean;
}

/**
 * Stripe payment information
 */
export interface StripePaymentInfo {
  payment_intent_id?: string | null;
  session_id?: string | null;
  amount: number;
  currency: string;
  status: string;
  payment_method_type?: string | null;
  payment_method_brand?: string | null;
  payment_method_last4?: string | null;
  payment_date: string;
  amount_received?: number | null;
  application_fee_amount?: number | null;
  net_amount?: number | null;
  available_at?: string | null;
  refund_amount?: number | null;
  refund_date?: string | null;
  customer_country?: string | null;
  customer_email?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
}

/**
 * Credit purchase transaction with payment details
 */
export interface CreditPurchaseTransaction {
  transaction_id: number;
  user_id: number;
  user_name: string;
  user_email: string;
  credits_amount: number;
  credits_available_date: string;
  payment_info?: StripePaymentInfo | null;
  euros_amount?: number | null;
  description: string;
}

/**
 * Accounting summary
 */
export interface AccountingSummary {
  total_paid: number;
  total_refunded: number;
  total_stripe_fees: number;
  net_total: number;
  total_transactions: number;
  available_balance?: number | null;
}

/**
 * Accounting data response
 */
export interface AccountingResponse {
  summary: AccountingSummary;
  transactions: CreditPurchaseTransaction[];
}

/**
 * Support ticket status values
 */
export type SupportTicketStatus =
  | 'open'
  | 'waiting_user'
  | 'waiting_support'
  | 'resolved'
  | 'closed';

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
  | 'other';

/**
 * Support topic metadata for UI
 */
export interface SupportTopicOption {
  value: SupportTicketTopic;
  label: string;
  description: string;
}

/**
 * Support attachment metadata
 */
export interface SupportAttachment {
  id: number;
  url: string;
  original_filename: string;
  content_type: string;
  created_at: string;
}

/**
 * Support message
 */
export interface SupportMessage {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_name: string;
  sender_role: UserRole;
  content: string;
  attachments: SupportAttachment[];
  created_at: string;
}

/**
 * Support ticket summary
 */
export interface SupportTicketSummary {
  id: number;
  user_id: number;
  user_name: string;
  topic: SupportTicketTopic;
  subject: string;
  description: string;
  status: SupportTicketStatus;
  created_at: string;
  updated_at?: string | null;
  last_message_at?: string | null;
  closed_at?: string | null;
  messages_count: number;
  attachments_count: number;
}

/**
 * Detailed support ticket with conversation
 */
export interface SupportTicketDetail extends Omit<SupportTicketSummary, 'messages_count'> {
  attachments: SupportAttachment[];
  messages: SupportMessage[];
}

/**
 * Email account type
 */
export type EmailAccountType = 'custom_domain' | 'gmail_oauth';

/**
 * Email account interface
 */
export interface EmailAccount {
  /** Unique identifier */
  id: number;
  /** User ID */
  user_id: number;
  /** Account type */
  account_type: EmailAccountType;
  /** Email address */
  email: string;
  /** Sender name */
  name: string;
  /** Whether account is verified */
  is_verified: boolean;
  /** Whether this is the default account */
  is_default: boolean;
  /** Whether account is active */
  is_active: boolean;
  /** Domain name (for custom_domain) */
  domain?: string | null;
  /** SPF verified status */
  spf_verified: boolean;
  /** DKIM verified status */
  dkim_verified: boolean;
  /** OAuth token expiration (for gmail_oauth) */
  oauth_token_expires_at?: string | null;
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at?: string | null;
}

/**
 * Email template interface
 */
export interface EmailTemplate {
  /** Unique identifier */
  id: number;
  /** User ID */
  user_id: number;
  /** Associated email account ID */
  email_account_id?: number | null;
  /** Template name */
  name: string;
  /** Email subject */
  subject: string;
  /** Email HTML body */
  body_html: string;
  /** List of variable names */
  variables?: string[];
  /** Whether template is active */
  is_active: boolean;
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at?: string | null;
}

/**
 * Email status
 */
export type EmailStatus = 
  | 'pending' 
  | 'sending' 
  | 'sent' 
  | 'delivered' 
  | 'opened' 
  | 'clicked' 
  | 'bounced' 
  | 'failed' 
  | 'complained';

/**
 * Email log interface
 */
export interface EmailLog {
  /** Unique identifier */
  id: number;
  /** User ID */
  user_id: number;
  /** Email account ID */
  email_account_id: number;
  /** Prospect ID */
  prospect_id?: string | null;
  /** Campaign ID */
  campaign_id?: string | null;
  /** Recipient email */
  recipient_email: string;
  /** Recipient name */
  recipient_name?: string | null;
  /** Email subject */
  subject: string;
  /** Email status */
  status: EmailStatus;
  /** Email provider */
  provider: string;
  /** Provider message ID */
  provider_message_id?: string | null;
  /** Sent timestamp */
  sent_at?: string | null;
  /** Delivered timestamp */
  delivered_at?: string | null;
  /** Opened timestamp */
  opened_at?: string | null;
  /** Clicked timestamp */
  clicked_at?: string | null;
  /** Bounced timestamp */
  bounced_at?: string | null;
  /** Failed timestamp */
  failed_at?: string | null;
  /** Error message */
  error_message?: string | null;
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at?: string | null;
}

/**
 * Email account creation request (custom domain)
 */
export interface EmailAccountCreateCustomDomain {
  email: string;
  name: string;
  domain: string;
  is_default?: boolean;
}

/**
 * Email account creation request (Gmail OAuth)
 */
export interface EmailAccountCreateGmail {
  email: string;
  name: string;
  oauth_code: string;
  is_default?: boolean;
}

/**
 * Email template creation request
 */
export interface EmailTemplateCreate {
  name: string;
  subject: string;
  body_html: string;
  email_account_id?: number;
  variables?: string[];
}

/**
 * Email template update request
 */
export interface EmailTemplateUpdate {
  name?: string;
  subject?: string;
  body_html?: string;
  email_account_id?: number;
  variables?: string[];
  is_active?: boolean;
}

/**
 * Send email request
 */
export interface SendEmailRequest {
  email_account_id: number;
  recipient_email: string;
  recipient_name?: string;
  subject: string;
  body_html: string;
  prospect_id?: string;
  template_id?: number;
  variables?: Record<string, string>;
}

/**
 * Send campaign email request
 */
export interface SendCampaignEmailRequest {
  email_account_id: number;
  campaign_id: string;
  template_id: number;
  prospect_ids: string[];
  variables_per_prospect?: Record<string, Record<string, string>>;
}

/**
 * Email stats response
 */
export interface EmailStats {
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_failed: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
}

/**
 * DNS verification response
 */
export interface DNSVerificationResponse {
  spf_verified: boolean;
  dkim_verified: boolean;
  is_verified: boolean;
  spf_record?: string | null;
  dkim_record?: string | null;
  instructions: string;
}