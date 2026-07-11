/**
 * Domain types for acquisition sequences (the auto-chaining tunnel).
 * Mirrors the API schemas in ``api/schemas/acquisition.py``.
 */

/** Lifecycle of a whole sequence. */
export type SequenceStatus = 'draft' | 'running' | 'paused' | 'awaiting_review' | 'completed' | 'cancelled' | 'failed'

/** How far the machine goes on its own. */
export type SequenceMode = 'semi_auto' | 'full_auto'

/** Per-prospect position in the state machine. */
export type SequenceStep =
  | 'found'
  | 'enriching'
  | 'enriched'
  | 'generating'
  | 'generated'
  | 'campaigning'
  | 'skipped'
  | 'failed'

/** Derived, always-fresh counters for a sequence. */
export interface SequenceStats {
  total: number
  by_step: Record<string, number>
  won: number
  emails_sent: number
  credits_spent: number
}

/** One prospect flowing through a sequence. */
export interface SequenceItem {
  id: number
  prospect_id: number
  prospect_name: string | null
  prospect_city: string | null
  prospect_email: string | null
  step: SequenceStep
  step_reason: string | null
  demo_site_id: number | null
  demo_slug: string | null
  demo_url: string | null
  demo_status: string | null
  won: boolean
  updated_at: string | null
}

/** Summary of a sequence (list view). */
export interface Sequence {
  id: number
  name: string
  status: SequenceStatus
  mode: SequenceMode
  auto_enrich: boolean
  auto_generate: boolean
  template_id: string | null
  auto_campaign: boolean
  email_template_id_a: number | null
  email_template_id_b: number | null
  send_delay_minutes: number
  campaign_id: number | null
  max_credits: number | null
  daily_email_cap: number | null
  review_approved_at: string | null
  created_at: string
  updated_at: string | null
  stats: SequenceStats
}

/** Full sequence with its per-prospect items. */
export interface SequenceDetail extends Sequence {
  items: SequenceItem[]
}

/** A follow-up step configured on a sequence's campaign. */
export interface SequenceFollowUpInput {
  template_id: number
  delay_days: number
}

/** Payload to create a sequence from a batch of already-found prospects. */
export interface SequenceCreatePayload {
  name: string
  prospect_ids: number[]
  mode: SequenceMode
  auto_enrich: boolean
  auto_generate: boolean
  template_id: string | null
  auto_campaign: boolean
  email_template_id_a: number | null
  email_template_id_b: number | null
  send_delay_minutes: number
  follow_ups: SequenceFollowUpInput[]
  max_credits: number | null
  daily_email_cap: number | null
}

/** Paginated sequence list. */
export interface SequenceListResponse {
  sequences: Sequence[]
  total: number
}
