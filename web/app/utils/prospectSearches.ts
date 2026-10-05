import type {
  ProspectSearchCandidate,
  ProspectSearchDetail,
  ProspectSearchLeadCriterion,
  ProspectSearchPageLocation,
  ProspectSearchPrefill,
  ProspectSearchStatus,
  ProspectSearchSummary,
  ProspectSearchTradeCounts,
} from '~/types/ProspectSearch'
import type { StatusPresentation } from '~/types/StatusPresentation'
import {
  PROSPECT_SEARCH_CHANNEL_OBJECTIVE_LABELS,
  PROSPECT_SEARCH_EMAIL_PROOF_LABELS,
  PROSPECT_SEARCH_LEAD_QUALITY_PRESENTATION,
  PROSPECT_SEARCH_MINIMUM_REVIEWS_FOR_RATING,
  PROSPECT_SEARCH_PAGE_PATH,
  PROSPECT_SEARCH_REQUEST_COST_DOLLARS,
  PROSPECT_SEARCH_VALIDATION_OBJECTIVE_LABELS,
} from '~/constants/prospectSearch'
import { ProspectCountries } from '~/utils/prospectCountries'

const LOCALE: string = 'fr-FR'

const ACTIVE_STATUSES: ProspectSearchStatus[] = ['pending', 'running', 'waiting_browser']

const SERVER_RUNNING_STATUSES: ProspectSearchStatus[] = ['pending', 'running']

const ACCENT_MARKS_PATTERN: RegExp = /[̀-ͯ]/g
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
   * Whether the server itself is still searching, which leaves no room for another search.
   * @param status - Status of the search.
   * @returns True while the server runs the search.
   */
  static isRunningOnServer(status: ProspectSearchStatus): boolean {
    return SERVER_RUNNING_STATUSES.includes(status)
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
   * Candidates of a search that already are prospects (accepted by hand, or let in by the automatic validation).
   * @param search - The search with its candidates.
   * @returns How many prospects the search created.
   */
  static createdProspectCount(search: ProspectSearchDetail): number {
    return search.candidates.filter(
      (candidate: ProspectSearchCandidate): boolean =>
        candidate.status !== 'rejected' && candidate.prospect_id !== null,
    ).length
  }

  /**
   * Leave the journal and the candidates out of a search.
   * @param detail - The search as its detail route returns it.
   * @returns The same search, as the lists and the activity route carry it.
   */
  static summaryOf(detail: ProspectSearchDetail): ProspectSearchSummary {
    const { journal: _journal, candidates: _candidates, ...summary }: ProspectSearchDetail = detail
    return summary
  }

  /**
   * Trades of the search, by their catalog label (the typed words while the totals are not known yet).
   * @param search - The search to read.
   * @returns The labels, joined by commas.
   */
  static tradesLabel(search: ProspectSearchSummary): string {
    return ProspectSearches.tradeLabels(search).join(', ')
  }

  /**
   * Trades of the search in a sentence, so that a list of searches stays readable.
   * @param search - The search to read.
   * @returns E.g. « Garage automobile et Couvreur ».
   */
  static tradesInWords(search: ProspectSearchSummary): string {
    const labels: string[] = ProspectSearches.tradeLabels(search)
    const lastLabel: string | undefined = labels.pop()
    return labels.length > 0 ? `${labels.join(', ')} et ${lastLabel}` : (lastLabel ?? '')
  }

  /**
   * Where the search looks: its country, then its towns when the user picked some.
   * @param search - The search to read.
   * @returns E.g. « France · Rennes, Nantes » or « Suisse · villes choisies par l'app ».
   */
  static placeLabel(search: Pick<ProspectSearchSummary, 'country' | 'cities'>): string {
    const country: string = ProspectCountries.option(search.country).label
    return `${country} · ${search.cities.length > 0 ? search.cities.join(', ') : "villes choisies par l'app"}`
  }

  /**
   * The objective of a search on one line: how many, reachable how, where, under which criteria.
   * @param search - The search to read.
   * @returns E.g. « 5 par métier · joignables par email · France · Rennes · sans site web · vous validez chaque lead ».
   */
  static objectiveLabel(search: ProspectSearchSummary): string {
    const parts: string[] = [
      `${search.count_per_trade} par métier`,
      PROSPECT_SEARCH_CHANNEL_OBJECTIVE_LABELS[search.channel],
      ProspectSearches.placeLabel(search),
    ]
    if (search.only_without_website) parts.push('sans site web')
    if (search.minimum_rating !== null) {
      parts.push(`note Google d'au moins ${ProspectSearches.ratingLabel(search.minimum_rating)}`)
    }
    parts.push(PROSPECT_SEARCH_VALIDATION_OBJECTIVE_LABELS[search.validation_mode])
    return parts.join(' · ')
  }

  /**
   * Estimated cost of a search, from the requests it spent.
   * @param requestCount - Requests sent so far.
   * @returns E.g. « env. 0,24 $ · 160 requêtes ».
   */
  static costLabel(requestCount: number): string {
    return `env. ${ProspectSearches.dollarsLabel(requestCount)} · ${requestCount.toLocaleString(LOCALE)} requête${requestCount > 1 ? 's' : ''}`
  }

  /**
   * What a number of requests costs.
   * @param requestCount - Requests sent, or planned.
   * @returns E.g. « 0,24 $ ».
   */
  static dollarsLabel(requestCount: number): string {
    const dollars: string = (requestCount * PROSPECT_SEARCH_REQUEST_COST_DOLLARS).toLocaleString(LOCALE, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
    return `${dollars} $`
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

  /**
   * Where to send the user to start a search, with the values another screen already knows.
   * @param prefill - Trade, town and country to hand over, if any.
   * @returns The new-search page, its query carrying the prefill.
   */
  static newSearchLocation(prefill: ProspectSearchPrefill = {}): ProspectSearchPageLocation {
    const query: Record<string, string> = {}
    if (prefill.category) query.category = prefill.category
    if (prefill.city) query.city = prefill.city
    if (prefill.country) query.country = prefill.country
    return { path: PROSPECT_SEARCH_PAGE_PATH, query }
  }

  /**
   * The town a lead is in: the one read on its listing, else the one the search was looking in.
   * @param candidate - The lead to read.
   * @returns The town, or null when neither is known.
   */
  static leadTown(candidate: ProspectSearchCandidate): string | null {
    return candidate.city ?? candidate.searched_city
  }

  /**
   * How complete a lead is, from the place the search gave it.
   * @param candidate - The lead to read.
   * @returns The quality label and its badge class.
   */
  static leadQuality(candidate: ProspectSearchCandidate): StatusPresentation {
    return (
      PROSPECT_SEARCH_LEAD_QUALITY_PRESENTATION[candidate.status] ?? {
        label: 'À vérifier',
        badgeClass: 'app-badge--progress',
      }
    )
  }

  /**
   * The four things a lead is judged on, each with what the search found for it.
   * @param candidate - The lead to read.
   * @returns Email, mobile, absence of website and Google rating, in that order.
   */
  static leadCriteria(candidate: ProspectSearchCandidate): ProspectSearchLeadCriterion[] {
    return [
      ProspectSearches.emailCriterion(candidate),
      ProspectSearches.mobileCriterion(candidate),
      ProspectSearches.noWebsiteCriterion(candidate),
      ProspectSearches.ratingCriterion(candidate),
    ]
  }

  /**
   * Trades of the search, by their catalog label (the typed words while the totals are not known yet).
   * @param search - The search to read.
   * @returns A fresh list of labels.
   */
  private static tradeLabels(search: ProspectSearchSummary): string[] {
    return search.trade_counts.length > 0
      ? search.trade_counts.map((counts: ProspectSearchTradeCounts): string => counts.label)
      : [...search.trades]
  }

  /**
   * Tell whether a lead has an email, and how well it is proven.
   * @param candidate - The lead to read.
   * @returns Verified when the business or a directory publishes it, to check when it is guessed.
   */
  private static emailCriterion(candidate: ProspectSearchCandidate): ProspectSearchLeadCriterion {
    const icon: string = 'i-lucide-mail'
    if (!candidate.email) return { key: 'email', icon, state: 'missing', label: "Pas d'email" }
    if (candidate.email_proof_level === 'a' || candidate.email_proof_level === 'b') {
      const proof: string = PROSPECT_SEARCH_EMAIL_PROOF_LABELS[candidate.email_proof_level]
      return { key: 'email', icon, state: 'verified', label: `Email ${proof}` }
    }
    return { key: 'email', icon, state: 'toCheck', label: 'Email sans preuve franche, à vérifier' }
  }

  /**
   * Tell whether a lead can be reached on a mobile number.
   * @param candidate - The lead to read.
   * @returns Verified for a mobile number, missing for a landline or no phone at all.
   */
  private static mobileCriterion(candidate: ProspectSearchCandidate): ProspectSearchLeadCriterion {
    const icon: string = 'i-lucide-smartphone'
    if (candidate.phone && candidate.phone_is_mobile) {
      return { key: 'mobile', icon, state: 'verified', label: 'Numéro de portable' }
    }
    return {
      key: 'mobile',
      icon,
      state: 'missing',
      label: candidate.phone ? 'Pas de portable (ligne fixe seulement)' : 'Pas de téléphone',
    }
  }

  /**
   * Tell whether a lead has no working website.
   * @param candidate - The lead to read.
   * @returns Verified without a site (or with a dead or directory one), missing when its site is live.
   */
  private static noWebsiteCriterion(candidate: ProspectSearchCandidate): ProspectSearchLeadCriterion {
    const icon: string = 'i-lucide-globe-lock'
    if (!candidate.website) return { key: 'noWebsite', icon, state: 'verified', label: 'Pas de site web' }
    if (candidate.website_status === 'dead') {
      return { key: 'noWebsite', icon, state: 'verified', label: 'Site web en panne : compte comme sans site' }
    }
    if (candidate.website_status === 'placeholder') {
      return { key: 'noWebsite', icon, state: 'verified', label: 'Mini-site annuaire : compte comme sans site' }
    }
    if (candidate.website_status === 'live') {
      return { key: 'noWebsite', icon, state: 'missing', label: 'A déjà un site web' }
    }
    return { key: 'noWebsite', icon, state: 'toCheck', label: 'Site web trouvé, à vérifier' }
  }

  /**
   * Tell whether a lead has a Google rating read on enough reviews.
   * @param candidate - The lead to read.
   * @returns Verified from three reviews, to check under that, missing without a rating.
   */
  private static ratingCriterion(candidate: ProspectSearchCandidate): ProspectSearchLeadCriterion {
    const icon: string = 'i-lucide-star'
    const rating: number | null = candidate.google_rating
    if (rating === null) return { key: 'rating', icon, state: 'missing', label: 'Pas de note Google' }
    const reviewCount: number = candidate.google_reviews_count ?? 0
    const ratingLabel: string = `Note Google ${ProspectSearches.ratingLabel(rating)}`
    if (reviewCount < PROSPECT_SEARCH_MINIMUM_REVIEWS_FOR_RATING) {
      return { key: 'rating', icon, state: 'toCheck', label: `${ratingLabel}, lue sur trop peu d'avis` }
    }
    return {
      key: 'rating',
      icon,
      state: 'verified',
      label: `${ratingLabel} · ${reviewCount.toLocaleString(LOCALE)} avis`,
    }
  }
}
