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
