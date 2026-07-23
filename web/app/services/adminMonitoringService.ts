import { ApiClient } from './api'

/**
 * Admin monitoring service — reads the reactive scraping diagnostics (source health,
 * incidents, captured HTML) exposed by the admin-only API.
 * @module services/adminMonitoringService
 */

/** Health summary for one scraping source over the last 24 h. */
export type ScraperSourceHealth = {
  source: string
  latest_status: string
  latest_at: string | null
  runs_24h: number
  incidents_24h: number
  last_ok_at: string | null
  latest_incident_id: number | null
}

/** System + scraping health overview. */
export type MonitoringOverview = {
  database: string
  diagnostics_total: number
  sources: ScraperSourceHealth[]
}

/** One recorded source-run outcome. */
export type ScraperIncident = {
  id: number
  source: string
  status: string
  category: string | null
  city: string | null
  results_count: number
  expected_count: number | null
  error_message: string | null
  has_html: boolean
  created_at: string | null
}

export class AdminMonitoringService {
  /**
   * Fetch the system + per-source scraping health overview.
   * @returns The monitoring overview.
   */
  static async getMonitoringOverview(): Promise<MonitoringOverview> {
    return ApiClient.get<MonitoringOverview>('/api/v1/admin/monitoring/overview')
  }

  /**
   * Fetch recent scraper incidents (per-source run outcomes).
   * @param limit - Maximum rows (1-500).
   * @param source - Optional source filter.
   * @returns The incident list.
   */
  static async getScraperIncidents(limit: number = 100, source?: string): Promise<{ items: ScraperIncident[] }> {
    return ApiClient.get<{ items: ScraperIncident[] }>('/api/v1/admin/monitoring/scrapers/incidents', {
      params: { limit, source: source ?? undefined },
    })
  }

  /**
   * Fetch the raw HTML captured for a blocked-source incident (as plain text).
   * @param incidentId - The diagnostic id.
   * @returns The captured HTML markup.
   */
  static async getScraperIncidentHtml(incidentId: number): Promise<string> {
    return ApiClient.get<string>(`/api/v1/admin/monitoring/scrapers/incidents/${incidentId}/html`)
  }
}
