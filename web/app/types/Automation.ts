import type { DemoSiteTheme } from '~/services/demoSiteService'
/**
 * Domain types for automatisations (the auto-chaining tunnel).
 * Mirrors the API schemas in ``api/schemas/acquisition.py``.
 */

/** Lifecycle of a whole automatisation. */
export type AutomationStatus = 'draft' | 'running' | 'paused' | 'awaiting_review' | 'completed' | 'cancelled' | 'failed'

/** How far the machine goes on its own. */
export type AutomationMode = 'semi_auto' | 'full_auto'

/** Per-prospect position in the state machine. */
export type AutomationStep =
  | 'found'
  | 'enriching'
  | 'enriched'
  | 'generating'
  | 'generated'
  | 'campaigning'
  | 'skipped'
  | 'failed'

/** Derived, always-fresh counters for an automatisation. */
export type AutomationStats = {
  total: number
  by_step: Record<string, number>
  won: number
  emails_sent: number
  credits_spent: number
}

/** One prospect flowing through an automatisation. */
export type AutomationItem = {
  id: number
  prospect_id: number
  prospect_name: string | null
  prospect_city: string | null
  prospect_email: string | null
  step: AutomationStep
  step_reason: string | null
  template_id: string | null
  demo_site_id: number | null
  demo_slug: string | null
  demo_url: string | null
  demo_status: string | null
  storyblok_editor_url: string | null
  quality_score: number | null
  quality_flags: string[] | null
  won: boolean
  updated_at: string | null
}

/** Summary of an automatisation (list view). */
export type Automation = {
  id: number
  name: string
  status: AutomationStatus
  mode: AutomationMode
  auto_enrich: boolean
  auto_generate: boolean
  template_id: string | null
  theme: DemoSiteTheme | null
  auto_campaign: boolean
  email_template_id_a: number | null
  email_template_id_b: number | null
  send_delay_minutes: number
  search_metiers: string[] | null
  search_villes: string[] | null
  target_days: number | null
  only_without_website: boolean
  campaign_id: number | null
  review_approved_at: string | null
  created_at: string
  updated_at: string | null
  stats: AutomationStats
  note: string | null
}

/** Full automatisation with its per-prospect items. */
export interface AutomationDetail extends Automation {
  items: AutomationItem[]
}

/** A follow-up step configured on an automatisation's campaign. */
export type AutomationFollowUpInput = {
  template_id: number
  delay_days: number
}

/** Payload to create an automatisation (selection or full-auto query). */
export type AutomationCreatePayload = {
  name: string
  mode: AutomationMode
  prospect_ids: number[]
  search_metiers: string[]
  search_villes: string[]
  target_days: number | null
  only_without_website: boolean
  auto_enrich: boolean
  auto_generate: boolean
  template_id: string | null
  theme: DemoSiteTheme | null
  auto_campaign: boolean
  email_template_id_a: number | null
  email_template_id_b: number | null
  send_delay_minutes: number
  follow_ups: AutomationFollowUpInput[]
}

/** Paginated automatisation list (the API keeps the ``sequences`` key). */
export type AutomationListResponse = {
  sequences: Automation[]
  total: number
}

export type EmailPreview = {
  subject: string
  body_html: string
}

export type SendPolicy = {
  daily_cap: number
  days_of_week: number[]
  window_start_hour: number
  window_end_hour: number
  spacing_minutes: number
}
