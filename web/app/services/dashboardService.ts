import { api } from './api'

/** Aggregated KPIs for the dashboard home page. */
export type DashboardStats = {
  prospects_total: number
  demo_sites_active: number
  campaigns_active: number
  emails_sent: number
  emails_opened: number
  emails_clicked: number
  open_rate: number
  click_rate: number
  orders_total: number
  sales_won: number
  revenue_cents: number
  pipeline_cents: number
  currency: string
}

/** A hot/warm lead surfaced on the dashboard. */
export type HotLead = {
  prospect_id: number
  name: string
  city: string | null
  temperature: string
  score: number
  last_seen: string | null
  signals: Record<string, number | string | null>
}

/** Hot leads list response. */
export type HotLeadsResponse = {
  items: HotLead[]
}

/** Email activity counters for a single day. */
export type ActivityPoint = {
  date: string
  sent: number
  opened: number
  clicked: number
}

/** Daily email activity series response. */
export type DashboardActivityResponse = {
  days: ActivityPoint[]
}

/**
 * Fetch the dashboard home KPIs for the current user.
 * @param periodDays - Rolling window in days (0 = all time).
 * @returns Aggregated dashboard stats.
 */
export async function getDashboardStats(periodDays: number = 0): Promise<DashboardStats> {
  return api.get<DashboardStats>('/api/v1/dashboard/stats', { params: { period_days: periodDays } })
}

/**
 * Fetch the current user's hottest leads (demo + email engagement).
 * @returns The hot leads list.
 */
export async function getHotLeads(): Promise<HotLeadsResponse> {
  return api.get<HotLeadsResponse>('/api/v1/dashboard/hot-leads')
}

/**
 * Fetch the daily email activity series for the trend chart.
 * @param days - Number of days to look back (1-90).
 * @returns The daily activity series.
 */
export async function getDashboardActivity(days: number = 14): Promise<DashboardActivityResponse> {
  return api.get<DashboardActivityResponse>(`/api/v1/dashboard/activity?days=${days}`)
}

/** Prospect count for one city. */
export type CoverageCity = {
  city: string
  count: number
}

/** An organization member selectable as a coverage scope. */
export type CoverageMember = {
  user_id: number
  name: string
}

/** Prospection coverage aggregated by city. */
export type CoverageResponse = {
  scope: string
  cities: CoverageCity[]
  total_prospects: number
  members: CoverageMember[]
  /** Distinct trades present in the scope (unfiltered) — feeds the trade selector. */
  available_categories: string[]
}

/**
 * Fetch the prospection coverage (prospect counts by city) for a scope.
 * @param scope - 'me' (my prospects), 'org' (whole organization), or 'member'.
 * @param memberId - Member user id when scope is 'member'.
 * @param categories - Optional trade filter (empty = all trades).
 * @returns The coverage aggregation + selectable members + available trades.
 */
export async function getCoverage(
  scope: string = 'me',
  memberId?: number,
  categories: string[] = [],
): Promise<CoverageResponse> {
  const params = new URLSearchParams({ scope })
  if (memberId != null) params.set('member_id', String(memberId))
  for (const category of categories) params.append('categories', category)
  return api.get<CoverageResponse>(`/api/v1/dashboard/coverage?${params.toString()}`)
}

/** Light prospect recap for the coverage zone drawer. */
export type CoverageProspectRow = {
  id: number
  name: string
  city: string | null
  category: string | null
  has_demo: boolean
  emails_sent: number
  emails_opened: number
  emails_clicked: number
  is_sold: boolean
}

/** Prospects of a coverage zone. */
export type CoverageProspectsResponse = {
  items: CoverageProspectRow[]
  total: number
}

/**
 * Fetch the prospects of a coverage zone (one city, or a region's cities).
 * @param cities - City names of the zone.
 * @param scope - 'me' | 'org' | 'member'.
 * @param memberId - Member user id when scope is 'member'.
 * @param categories - Optional trade filter (empty = all trades).
 * @returns Light prospect rows + real total.
 */
export async function getCoverageProspects(
  cities: string[],
  scope: string = 'me',
  memberId?: number,
  categories: string[] = [],
): Promise<CoverageProspectsResponse> {
  const params = new URLSearchParams({ scope })
  if (memberId != null) params.set('member_id', String(memberId))
  for (const city of cities) params.append('cities', city)
  for (const category of categories) params.append('categories', category)
  return api.get<CoverageProspectsResponse>(`/api/v1/dashboard/coverage/prospects?${params.toString()}`)
}
