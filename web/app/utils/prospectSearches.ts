import type {
  ProspectSearchDetail,
  ProspectSearchCandidate,
  ProspectSearchStatus,
  ProspectSearchSummary,
  ProspectSearchTradeCounts,
} from '~/types/ProspectSearch'
import { PROSPECT_SEARCH_REQUEST_COST_DOLLARS } from '~/constants/prospectSearch'
import { ProspectCountries } from '~/utils/prospectCountries'

const LOCALE: string = 'fr-FR'

const ACTIVE_STATUSES: ProspectSearchStatus[] = ['pending', 'running', 'waiting_browser']

const ACCENT_MARKS_PATTERN: RegExp = /[\u0300-\u036f]/g
const SPACES_AND_HYPHENS_PATTERN: RegExp = /[\s-]+/g
const HTTP_URL_PATTERN: RegExp = /^https?:\/\//i
const URL_SCHEME_PATTERN: RegExp = /^[a-z][a-z0-9+.-]*:/i
const LEADING_SLASHES_PATTERN: RegExp = /^\/+/

/** Reading rules of a prospect search: what its status allows, what it found, what it cost. */
export class ProspectSearches {
  private constructor() {}

  /**
   * Whether the search still moves on its own (server run, or Facebook pages waiting for a desktop).
   * @param status - Status of the search.
   * @returns True while the search has to be followed.
   */
  static isActive(status: ProspectSearchStatus): boolean {
    return ACTIVE_STATUSES.includes(status)
  }

  /**
   * Whether the search can be carried on: stopped, failed, or finished short of its objective.
   * @param search - The search to read.
   * @returns True when the search can be carried on.
   */
  static canResume(search: ProspectSearchSummary): boolean {
    if (search.status === 'cancelled' || search.status === 'failed') return true
    return (
      search.status === 'completed' &&
      search.trade_counts.some((counts: ProspectSearchTradeCounts): boolean => counts.kept < counts.wanted)
    )
  }

  /**
   * Prospects kept across every trade of the search.
   * @param search - The search to read.
   * @returns The kept total.
   */
  static keptCount(search: ProspectSearchSummary): number {
    return search.trade_counts.reduce(
      (total: number, counts: ProspectSearchTradeCounts): number => total + counts.kept,
      0,
    )
  }

  /**
   * Prospects asked across every trade of the search.
   * @param search - The search to read.
   * @returns The wanted total.
   */
  static wantedCount(search: ProspectSearchSummary): number {
    return search.trade_counts.reduce(
      (total: number, counts: ProspectSearchTradeCounts): number => total + counts.wanted,
      0,
    )
  }

  /**
   * Candidates the search turned into prospects (kept, or set aside for another channel).
   * @param search - The search with its candidates.
   * @returns How many prospects the search created.
   */
  static createdProspectCount(search: ProspectSearchDetail): number {
    return search.candidates.filter(
      (candidate: ProspectSearchCandidate): boolean => candidate.status === 'kept' || candidate.status === 'set_aside',
    ).length
  }

  /**
   * Trades of the search, by their catalog label (the typed words while the totals are not known yet).
   * @param search - The search to read.
   * @returns The labels, joined by commas.
   */
  static tradesLabel(search: ProspectSearchSummary): string {
    const labels: string[] =
      search.trade_counts.length > 0
        ? search.trade_counts.map((counts: ProspectSearchTradeCounts): string => counts.label)
        : search.trades
    return labels.join(', ')
  }

  /**
   * Where the search looks: its country, then its towns when the user picked some.
   * @param search - The search to read.
   * @returns E.g. « France · Rennes, Nantes » or « Suisse · villes choisies par l'app ».
   */
  static placeLabel(search: ProspectSearchSummary): string {
    const country: string = ProspectCountries.option(search.country).label
    return `${country} · ${search.cities.length > 0 ? search.cities.join(', ') : "villes choisies par l'app"}`
  }

  /**
   * Estimated cost of a search, from the requests it spent.
   * @param requestCount - Requests sent so far.
   * @returns E.g. « env. 0,24 $ · 160 requêtes ».
   */
  static costLabel(requestCount: number): string {
    const dollars: string = (requestCount * PROSPECT_SEARCH_REQUEST_COST_DOLLARS).toLocaleString(LOCALE, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
    return `env. ${dollars} $ · ${requestCount.toLocaleString(LOCALE)} requête${requestCount > 1 ? 's' : ''}`
  }

  /**
   * Google rating written the French way, with one decimal.
   * @param rating - Rating out of five.
   * @returns E.g. « 4,0 ».
   */
  static ratingLabel(rating: number): string {
    return rating.toLocaleString(LOCALE, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  }

  /**
   * Fold a typed label for comparison (lowercase, accent-free, single spaces).
   * @param label - Trade or town as typed.
   * @returns The comparable key.
   */
  static foldLabel(label: string): string {
    return label
      .normalize('NFD')
      .replace(ACCENT_MARKS_PATTERN, '')
      .toLowerCase()
      .replace(SPACES_AND_HYPHENS_PATTERN, ' ')
      .trim()
  }

  /**
   * Turn a scraped address into a link target, refusing anything that is not a web page.
   * @param url - Address read on a listing (may lack its scheme).
   * @returns An http(s) URL, or null when the value cannot be opened safely.
   */
  static externalHref(url: string | null | undefined): string | null {
    const trimmed: string = (url ?? '').trim()
    if (!trimmed) return null
    if (HTTP_URL_PATTERN.test(trimmed)) return trimmed
    if (URL_SCHEME_PATTERN.test(trimmed)) return null
    return `https://${trimmed.replace(LEADING_SLASHES_PATTERN, '')}`
  }
}
