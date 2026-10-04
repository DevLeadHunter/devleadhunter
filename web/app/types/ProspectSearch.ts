import type { ProspectCountry, ProspectWebsiteStatus } from '~/types'

export type ProspectSearchChannel = 'email' | 'sms' | 'email_and_sms'

export type ProspectSearchStatus = 'pending' | 'running' | 'waiting_browser' | 'completed' | 'cancelled' | 'failed'

export type ProspectSearchCandidateStatus =
  | 'discovered'
  | 'needs_browser'
  | 'kept'
  | 'set_aside'
  | 'to_confirm'
  | 'rejected'

export type ProspectSearchCandidateOrigin = 'google_local' | 'facebook_search' | 'registry_rge' | 'registry_rbq'

export type ProspectSearchRejectReason =
  | 'has_website'
  | 'closed'
  | 'homonym'
  | 'chain'
  | 'wrong_trade'
  | 'low_rating'
  | 'no_contact'
  | 'already_known'
  | 'do_not_contact'
  | 'previously_rejected'
  | 'manual'

/** How well an email is proven: `a` published by the business, `b` listed by a directory, `c` guessed. */
export type ProspectSearchEmailProofLevel = 'a' | 'b' | 'c'

export type ProspectSearchStopReason = 'budget' | 'towns'

export type ProspectSearchTradeOption = {
  key: string
  label: string
}

export type ProspectSearchCreatePayload = {
  trades: string[]
  country: ProspectCountry
  cities: string[]
  count_per_trade: number
  channel: ProspectSearchChannel
  only_without_website: boolean
  minimum_rating: number | null
}

export type ProspectSearchTradeCounts = {
  trade: string
  label: string
  wanted: number
  kept: number
  set_aside: number
  to_confirm: number
  waiting_browser: number
  rejected: number
  unverified: number
  towns: string[]
  stop_reason: ProspectSearchStopReason | null
}

export type ProspectSearchSummary = {
  id: number
  trades: string[]
  country: string
  cities: string[]
  count_per_trade: number
  channel: ProspectSearchChannel
  only_without_website: boolean
  minimum_rating: number | null
  status: ProspectSearchStatus
  request_count: number
  judge_call_count: number
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  trade_counts: ProspectSearchTradeCounts[]
}

export type ProspectSearchEvidenceLine = {
  fact: string
  value: string
  source: string
  url?: string | null
  snippet?: string | null
}

export type ProspectSearchCandidate = {
  id: number
  trade: string
  origin: ProspectSearchCandidateOrigin
  searched_city: string | null
  name: string
  address: string | null
  city: string | null
  country: string
  phone: string | null
  phone_is_mobile: boolean
  email: string | null
  email_proof_level: ProspectSearchEmailProofLevel | null
  website: string | null
  website_status: ProspectWebsiteStatus | null
  google_maps_url: string | null
  facebook_url: string | null
  google_rating: number | null
  google_reviews_count: number | null
  google_category: string | null
  owner_name: string | null
  registry_number: string | null
  status: ProspectSearchCandidateStatus
  reject_reason: ProspectSearchRejectReason | null
  reject_detail: string | null
  evidence: ProspectSearchEvidenceLine[]
  prospect_id: number | null
}

export type ProspectSearchJournalLine = {
  at: string
  message: string
}

export type ProspectSearchDetail = ProspectSearchSummary & {
  journal: ProspectSearchJournalLine[]
  candidates: ProspectSearchCandidate[]
}

/** A Facebook page the desktop app must read for a waiting candidate. */
export type ProspectSearchBrowserTask = {
  candidate_id: number
  name: string
  facebook_url: string
  country: string
}

export type ProspectSearchFacebookContact = {
  is_readable: boolean
  emails: string[]
  phone: string | null
  website: string | null
}

export type ProspectSearchFacebookReading = {
  searchId: number
  isRunning: boolean
  pagesRead: number
  pagesToRead: number
  currentBusinessName: string | null
  isChromeInstalling: boolean
  errorMessage: string | null
}

export type ProspectSearchResultTabKey = ProspectSearchCandidateStatus | 'journal'

export type ProspectSearchChannelOption = {
  value: ProspectSearchChannel
  label: string
  description: string
  icon: string
}
