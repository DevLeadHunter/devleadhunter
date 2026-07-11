import { api } from './api'

/** Aggregated KPIs for the dashboard home page. */
export interface DashboardStats {
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
export interface HotLead {
  prospect_id: number
  name: string
  city: string | null
  temperature: string
  score: number
  last_seen: string | null
  signals: Record<string, number | string | null>
}

/** Hot leads list response. */
export interface HotLeadsResponse {
  items: HotLead[]
}

/** Email activity counters for a single day. */
export interface ActivityPoint {
  date: string
  sent: number
  opened: number
  clicked: number
}

/** Daily email activity series response. */
export interface DashboardActivityResponse {
  days: ActivityPoint[]
}

/**
 * Fetch the dashboard home KPIs for the current user.
 * @returns Aggregated dashboard stats.
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/api/v1/dashboard/stats')
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
export interface CoverageCity {
  city: string
  count: number
}

/** An organization member selectable as a coverage scope. */
export interface CoverageMember {
  user_id: number
  name: string
}

/** Prospection coverage aggregated by city. */
export interface CoverageResponse {
  scope: string
  cities: CoverageCity[]
  total_prospects: number
  members: CoverageMember[]
}

/**
 * Fetch the prospection coverage (prospect counts by city) for a scope.
 * @param scope - 'me' (my prospects), 'org' (whole organization), or 'member'.
 * @param memberId - Member user id when scope is 'member'.
 * @returns The coverage aggregation + selectable members.
 */
export async function getCoverage(scope: string = 'me', memberId?: number): Promise<CoverageResponse> {
  const params: string = memberId != null ? `?scope=${scope}&member_id=${memberId}` : `?scope=${scope}`
  return api.get<CoverageResponse>(`/api/v1/dashboard/coverage${params}`)
}
