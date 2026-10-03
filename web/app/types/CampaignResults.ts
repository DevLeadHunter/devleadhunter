import type { UiKpiBandTrendBadge } from '~/types/UiKpiBand'

export type CampaignResultsProspectState =
  | 'sold'
  | 'interested'
  | 'refused'
  | 'replied'
  | 'visited'
  | 'silent'
  | 'pending'
  | 'not_sent'

export type CampaignResultsSendStatus = 'sent' | 'planned' | 'skipped' | 'failed'

export type CampaignResultsReplyVerdict = 'interested' | 'refused' | 'other'

export type CampaignResultsReplyChannel = 'email' | 'banner' | 'manual'

export type CampaignResultsSend = {
  step: number
  status: CampaignResultsSendStatus
  at: string
  is_bounced: boolean
}

export type CampaignResultsVisit = {
  started_at: string
  active_seconds: number
  device_type: string | null
}

export type CampaignResultsReply = {
  id: string
  prospect_id: number
  received_at: string
  verdict: CampaignResultsReplyVerdict
  channel: CampaignResultsReplyChannel
  answered_step: number
  excerpt: string
  is_handled: boolean
}

export type CampaignResultsProspect = {
  id: number
  name: string
  category: string
  city: string | null
  state: CampaignResultsProspectState
  is_email_undeliverable: boolean
  sends: CampaignResultsSend[]
  visits: CampaignResultsVisit[]
}

export type CampaignResultsTotals = {
  prospects: number
  contacted: number
  visited: number
  replied: number
  interested: number
  refused: number
  sales: number
  revenue_cents: number
  currency: string | null
  first_mails_sent: number
  follow_ups_sent: number
  bounced: number
  failed: number
  planned_first_mails: number
  planned_follow_ups: number
}

export type CampaignResultsResponse = {
  campaign_id: number
  generated_at: string
  is_visit_tracking_available: boolean
  totals: CampaignResultsTotals
  next_send: { at: string; prospect_name: string } | null
  last_planned_send_at: string | null
  demo_sites: { online: number; first_expiry_at: string | null; last_expiry_at: string | null }
  prospects: CampaignResultsProspect[]
  replies: CampaignResultsReply[]
}

export type CampaignBenchmark = {
  campaign_id: number
  name: string
  status: string
  started_at: string | null
  contacted: number
  visited: number
  replied: number
  interested: number
}

export type CampaignBenchmarksResponse = {
  campaigns: CampaignBenchmark[]
}

export type CampaignManualReplyPayload = {
  prospect_id: number
  verdict: CampaignResultsReplyVerdict
  received_at: string | null
  message: string
}

export type CampaignResultsStage = 'contacted' | 'visited' | 'replied' | 'interested'

export type CampaignResultsComparison = {
  key: string
  label: string
  referenceLabel: string
  contacted: number
  visited: number
  replied: number
  interested: number
}

/** One calendar day of the campaign, in the viewer's timezone. */
export type CampaignResultsDay = {
  key: string
  date: Date
  isWeekend: boolean
  isToday: boolean
  isFuture: boolean
  visits: number
  newVisitors: number
  firstMails: number
  followUps: number
  plannedFirstMails: number
  plannedFollowUps: number
  replies: CampaignResultsReply[]
}

export type CampaignResultsRow = {
  prospect: CampaignResultsProspect
  replies: CampaignResultsReply[]
  visitCount: number
  activeSeconds: number
  firstMailAt: Date | null
  lastVisitAt: Date | null
}

export type CampaignResultsPlannedSend = {
  step: number
  prospectName: string
  at: Date
}

export type CampaignResultsSendDayProgress = {
  current: number
  total: number
}

export type CampaignResultsFilterKey = 'all' | 'opened' | 'toRelaunch' | 'replied' | 'silent' | 'pending'

export type CampaignResultsSortKey = 'default' | 'visits' | 'activeTime' | 'lastVisit'

export type CampaignResultsSortDirection = 'ascending' | 'descending'

export type CampaignResultsRowReply = {
  row: CampaignResultsRow
  reply: CampaignResultsReply
}

export type CampaignResultsKpiComparison = {
  trendBadge: UiKpiBandTrendBadge | null
  comparisonNote: string
}

export type CampaignResultsTodoTone = 'green' | 'blue' | 'amber' | 'red'

export type CampaignResultsTodoAction =
  | { kind: 'prospect'; prospectId: number }
  | { kind: 'filter'; filter: CampaignResultsFilterKey }

export type CampaignResultsTodo = {
  key: string
  tone: CampaignResultsTodoTone
  icon: string
  title: string
  verdict: CampaignResultsReplyVerdict | null
  text: string
  actionLabel: string
  action: CampaignResultsTodoAction
}

export type CampaignResultsHeadline = {
  label: string
  title: string
  summary: string
}

export type CampaignResultsStateGroup = {
  state: CampaignResultsProspectState
  rows: CampaignResultsRow[]
}

export type CampaignResultsStateFact = {
  label: string
  value: string
  detail: string
}

export type CampaignResultsTradeGroup = {
  key: string
  label: string
  rows: CampaignResultsRow[]
  contacted: number
  visited: number
}

export type CampaignResultsStepSummary = {
  step: number
  label: string
  timingLabel: string
  sent: number
  planned: number
  cancelled: number
  firstPlannedAt: Date | null
  visitors: number
  replies: CampaignResultsReply[]
}

export type CampaignResultsVisitMarks = {
  medianDelayMinutes: number | null
  visitorsWithinHour: number
  visitors: number
  phoneVisits: number
  eveningVisits: number
  visits: number
}
