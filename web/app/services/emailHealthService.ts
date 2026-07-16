import { api } from './api'

/**
 * Email deliverability health service — feeds the « Santé email » page:
 * sending stats with thresholds, daily trends, per-provider breakdown,
 * DNS authentication, Gmail Postmaster reputation and the pre-send spam tester.
 * @module services/emailHealthService
 */

/** Raw counters + derived rates over one window. */
export interface EmailHealthStats {
  sent: number
  delivered: number
  opened: number
  clicked: number
  bounced: number
  complained: number
  suppressed: number
  failed: number
  delivery_rate: number
  open_rate: number
  click_rate: number
  bounce_rate: number
  complaint_rate: number
}

/** A health signal with its ok/warn/danger status. */
export interface EmailHealthSignal {
  key: string
  label: string
  value: number
  unit: string
  status: 'ok' | 'warn' | 'danger'
  hint: string
}

/** One sending account with its stats. */
export interface EmailHealthAccount {
  id: number
  email: string
  name: string
  account_type: string
  is_default: boolean
  is_active: boolean
  domain: string
  stats: EmailHealthStats
}

/** The overview payload. */
export interface EmailHealthOverview {
  period_days: number
  totals: EmailHealthStats & { unsubscribed: number; unsubscribe_rate: number }
  signals: EmailHealthSignal[]
  accounts: EmailHealthAccount[]
}

/** One daily point of the trend series. */
export interface EmailHealthTrendDay {
  date: string
  sent: number
  delivered: number
  opened: number
  bounced: number
  complained: number
  bounce_rate: number
  complaint_rate: number
  delivery_rate: number
}

/** Deliverability per recipient mailbox provider. */
export interface EmailHealthProvider {
  provider: string
  label: string
  domains: string[]
  sent: number
  delivered: number
  opened: number
  bounced: number
  complained: number
  delivery_rate: number
  open_rate: number
  bounce_rate: number
  complaint_rate: number
  status: 'ok' | 'warn' | 'danger'
  note: string
}

/** One deliverability incident (bounce, complaint, suppression, failure). */
export interface EmailHealthIncident {
  id: number
  kind: 'bounced' | 'complained' | 'suppressed' | 'failed'
  recipient_email: string
  subject: string
  campaign_id: number | null
  error_message: string | null
  at: string | null
}

/** One DNS check result (status + explanation). */
export interface EmailDnsCheck {
  status: 'ok' | 'warn' | 'danger'
  detail: string
  record?: string | null
  policy?: string | null
  rua?: string | null
  selectors?: string[]
  hosts?: string[]
  lists?: { list: string; status: 'ok' | 'listed' | 'unknown' }[]
}

/** DNS health for one sending domain. */
export interface EmailDnsDomain {
  domain: string
  spf: EmailDnsCheck
  dkim: EmailDnsCheck
  dmarc: EmailDnsCheck
  mx: EmailDnsCheck
  blocklists: EmailDnsCheck
}

/** One daily Gmail Postmaster stat. */
export interface PostmasterDay {
  date: string
  domain_reputation: string | null
  user_reported_spam_ratio: number | null
  spf_success_ratio: number | null
  dkim_success_ratio: number | null
  dmarc_success_ratio: number | null
  inbound_encryption_ratio: number | null
}

/** Gmail Postmaster payload for one domain. */
export interface PostmasterDomain {
  configured: boolean
  domain: string
  reason?: string
  error?: string
  latest?: PostmasterDay | null
  days?: PostmasterDay[]
}

/** SpamAssassin verdict for a draft. */
export interface SpamAssassinResult {
  available: boolean
  error?: string
  score?: number
  status?: 'ok' | 'warn' | 'danger'
  rules?: { score: string | number | null; description: string | null }[]
}

/** One local heuristic check on a draft. */
export interface SpamLocalCheck {
  key: string
  label: string
  status: 'ok' | 'warn' | 'danger'
  detail: string
}

/** The spam tester payload. */
export interface SpamTestResult {
  spamassassin: SpamAssassinResult
  checks: SpamLocalCheck[]
}

/**
 * Fetch the deliverability overview (totals, signals, per-account stats).
 * @param periodDays - Rolling window: 7, 30 or 90 days.
 * @returns The overview payload.
 */
export async function getEmailHealthOverview(periodDays: number): Promise<EmailHealthOverview> {
  return api.get<EmailHealthOverview>('/api/v1/email-health/overview', { params: { period_days: periodDays } })
}

/**
 * Fetch the daily trend series (cohort by send day).
 * @param periodDays - Rolling window: 7, 30 or 90 days.
 * @returns The daily points.
 */
export async function getEmailHealthTrends(periodDays: number): Promise<{ days: EmailHealthTrendDay[] }> {
  return api.get<{ days: EmailHealthTrendDay[] }>('/api/v1/email-health/trends', {
    params: { period_days: periodDays },
  })
}

/**
 * Fetch the deliverability breakdown per recipient mailbox provider.
 * @param periodDays - Rolling window: 7, 30 or 90 days.
 * @returns The provider list, sorted by volume.
 */
export async function getEmailHealthProviders(periodDays: number): Promise<{ providers: EmailHealthProvider[] }> {
  return api.get<{ providers: EmailHealthProvider[] }>('/api/v1/email-health/providers', {
    params: { period_days: periodDays },
  })
}

/**
 * Fetch the recent deliverability incidents.
 * @param limit - Maximum rows.
 * @returns The incident journal, most recent first.
 */
export async function getEmailHealthIncidents(limit = 50): Promise<{ items: EmailHealthIncident[] }> {
  return api.get<{ items: EmailHealthIncident[] }>('/api/v1/email-health/incidents', { params: { limit } })
}

/**
 * Fetch the DNS authentication checks for every sending domain.
 * @returns SPF/DKIM/DMARC/MX/blocklists per domain.
 */
export async function getEmailHealthDns(): Promise<{ domains: EmailDnsDomain[] }> {
  return api.get<{ domains: EmailDnsDomain[] }>('/api/v1/email-health/dns')
}

/**
 * Fetch the Gmail Postmaster reputation for every sending domain.
 * @param periodDays - History depth.
 * @returns Per-domain reputation payloads (or the not-configured flag).
 */
export async function getEmailHealthPostmaster(periodDays: number): Promise<{ domains: PostmasterDomain[] }> {
  return api.get<{ domains: PostmasterDomain[] }>('/api/v1/email-health/postmaster', {
    params: { period_days: periodDays },
  })
}

/**
 * Score an email draft (SpamAssassin + local heuristics) before sending.
 * @param subject - Email subject.
 * @param bodyHtml - HTML body.
 * @returns The spam test verdicts.
 */
export async function runEmailSpamTest(subject: string, bodyHtml: string): Promise<SpamTestResult> {
  return api.post<SpamTestResult>('/api/v1/email-health/spam-test', { subject, body_html: bodyHtml })
}
