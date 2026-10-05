import type {
  ProspectSearchActivity,
  ProspectSearchBrowserTask,
  ProspectSearchCandidate,
  ProspectSearchCreatePayload,
  ProspectSearchDecisionsPayload,
  ProspectSearchDecisionsResult,
  ProspectSearchDetail,
  ProspectSearchFacebookContact,
  ProspectSearchSummary,
  ProspectSearchTradeOption,
} from '~/types/ProspectSearch'
import { ApiClient } from '~/services/api'
import { postToScraperSidecar } from '~/services/scraperSidecarService'

const BASE_URL: string = '/api/v1/prospect-searches'

const FACEBOOK_PAGE_READ_TIMEOUT_MS: number = 120_000

/** HTTP client of the objective-driven prospect search. */
export class ProspectSearchService {
  /**
   * List the trades the search knows how to recognise.
   * @returns The known trades.
   */
  static async listTrades(): Promise<ProspectSearchTradeOption[]> {
    return ApiClient.get<ProspectSearchTradeOption[]>(`${BASE_URL}/trades`)
  }

  /**
   * Create a search from an objective; the server starts it right away.
   * @param payload - Trades, country, towns, count per trade and contact channel.
   * @returns The created search.
   * @throws Error carrying the API message when the objective is refused.
   */
  static async createSearch(payload: ProspectSearchCreatePayload): Promise<ProspectSearchDetail> {
    return ApiClient.post<ProspectSearchDetail>(BASE_URL, payload)
  }

  /**
   * List the user's most recent searches with their totals.
   * @returns The searches, newest first.
   */
  static async listSearches(): Promise<ProspectSearchSummary[]> {
    return ApiClient.get<ProspectSearchSummary[]>(BASE_URL)
  }

  /**
   * Fetch a search with its journal and every candidate it looked at.
   * @param searchId - Identifier of the search.
   * @returns The search detail.
   */
  static async getSearch(searchId: number): Promise<ProspectSearchDetail> {
    return ApiClient.get<ProspectSearchDetail>(`${BASE_URL}/${searchId}`)
  }

  /**
   * Stop a search; what it found is kept.
   * @param searchId - Identifier of the search.
   * @returns The stopped search.
   */
  static async cancelSearch(searchId: number): Promise<ProspectSearchDetail> {
    return ApiClient.post<ProspectSearchDetail>(`${BASE_URL}/${searchId}/cancel`, {})
  }

  /**
   * Carry on a search that stopped short of its objective.
   * @param searchId - Identifier of the search.
   * @returns The search, running again.
   */
  static async resumeSearch(searchId: number): Promise<ProspectSearchDetail> {
    return ApiClient.post<ProspectSearchDetail>(`${BASE_URL}/${searchId}/resume`, {})
  }

  /**
   * List the Facebook pages a browser on the user's machine must read for a search.
   * @param searchId - Identifier of the search.
   * @returns One task per waiting candidate.
   */
  static async listBrowserTasks(searchId: number): Promise<ProspectSearchBrowserTask[]> {
    return ApiClient.get<ProspectSearchBrowserTask[]>(`${BASE_URL}/${searchId}/browser-tasks`)
  }

  /**
   * Read the contact block of a Facebook page with the Chrome of the user's machine.
   * @param task - The page to read.
   * @returns What the page publishes, or null outside the desktop app.
   * @throws Error when the local scraper fails or does not answer in time.
   */
  static async readFacebookPage(task: ProspectSearchBrowserTask): Promise<ProspectSearchFacebookContact | null> {
    return postToScraperSidecar<ProspectSearchFacebookContact>(
      '/scraper/facebook-contact',
      { business_name: task.name, facebook_url: task.facebook_url, country: task.country },
      { timeoutMs: FACEBOOK_PAGE_READ_TIMEOUT_MS },
    )
  }

  /**
   * Hand over what a browser read on a candidate's Facebook page.
   * @param searchId - Identifier of the search.
   * @param candidateId - Candidate whose page was read.
   * @param contact - What the page publishes.
   * @returns The candidate, placed by the server.
   */
  static async recordFacebookContact(
    searchId: number,
    candidateId: number,
    contact: ProspectSearchFacebookContact,
  ): Promise<ProspectSearchCandidate> {
    return ApiClient.post<ProspectSearchCandidate>(
      `${BASE_URL}/${searchId}/candidates/${candidateId}/facebook-contact`,
      contact,
    )
  }

  /**
   * Put a lead refused by hand back in the waiting list, at the place the search gave it.
   * @param searchId - Identifier of the search.
   * @param candidateId - Candidate refused a moment ago.
   * @returns The candidate, waiting for a decision again.
   * @throws Error carrying the API message when the lead was not refused by hand.
   */
  static async restoreCandidate(searchId: number, candidateId: number): Promise<ProspectSearchCandidate> {
    return ApiClient.post<ProspectSearchCandidate>(`${BASE_URL}/${searchId}/candidates/${candidateId}/restore`, {})
  }

  /**
   * Keep a candidate by hand: it becomes a prospect.
   * @param searchId - Identifier of the search.
   * @param candidateId - Candidate to keep.
   * @returns The kept candidate.
   * @throws Error carrying the API message when the business is already a prospect.
   */
  static async keepCandidate(searchId: number, candidateId: number): Promise<ProspectSearchCandidate> {
    return ApiClient.post<ProspectSearchCandidate>(`${BASE_URL}/${searchId}/candidates/${candidateId}/keep`, {})
  }

  /**
   * Discard a candidate by hand: no later search proposes it again.
   * @param searchId - Identifier of the search.
   * @param candidateId - Candidate to discard.
   * @returns The discarded candidate.
   * @throws Error carrying the API message when the candidate already became a prospect.
   */
  static async rejectCandidate(searchId: number, candidateId: number): Promise<ProspectSearchCandidate> {
    return ApiClient.post<ProspectSearchCandidate>(`${BASE_URL}/${searchId}/candidates/${candidateId}/reject`, {})
  }

  /**
   * List every candidate waiting for the user's decision, whatever the search it comes from.
   * @returns The waiting candidates, newest first.
   */
  static async listPendingCandidates(): Promise<ProspectSearchCandidate[]> {
    return ApiClient.get<ProspectSearchCandidate[]>(`${BASE_URL}/pending-candidates`)
  }

  /**
   * Read what the shell follows: how many candidates wait, the search still running, and whether the PC is on.
   * @param isFromDesktopApp - True from the desktop app, which reads the Facebook pages: the API then knows it is on.
   * @returns The waiting count, the active search if any, the queue and the desktop app presence.
   */
  static async getActivity(isFromDesktopApp: boolean): Promise<ProspectSearchActivity> {
    return ApiClient.get<ProspectSearchActivity>(`${BASE_URL}/activity`, {
      params: { from_desktop_app: isFromDesktopApp || undefined },
    })
  }

  /**
   * Accept and refuse several candidates at once.
   * @param payload - Candidates to accept and candidates to refuse.
   * @returns How many decisions were applied, and the ones the server refused with their reason.
   */
  static async decideCandidates(payload: ProspectSearchDecisionsPayload): Promise<ProspectSearchDecisionsResult> {
    return ApiClient.post<ProspectSearchDecisionsResult>(`${BASE_URL}/candidates/decisions`, payload)
  }
}
