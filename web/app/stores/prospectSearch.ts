/**
 * Shared prospect-search store — the objective-driven search followed by the page, the drawer and the tunnels.
 */
import type { ComputedRef, Ref } from 'vue'
import type { ScraperChromeHealth } from '~/services/scraperSidecarService'
import type {
  ProspectSearchBrowserTask,
  ProspectSearchCandidate,
  ProspectSearchCreatePayload,
  ProspectSearchDetail,
  ProspectSearchFacebookContact,
  ProspectSearchFacebookReading,
  ProspectSearchSummary,
  ProspectSearchTradeOption,
} from '~/types/ProspectSearch'
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { ProspectSearchService } from '~/services/prospectSearchService'
import { getScraperChromeHealth, getScraperSidecarInfo, requestChromeProvision } from '~/services/scraperSidecarService'
import { useUserStore } from '~/stores/user'
import { ProspectSearches } from '~/utils/prospectSearches'

const POLL_INTERVAL_MS: number = 2_500

const WAITING_FOR_DESKTOP_POLL_INTERVAL_MS: number = 15_000

const RECENT_SEARCHES_LIMIT: number = 30

const CHROME_INSTALL_CHECK_INTERVAL_MS: number = 10_000

const CHROME_INSTALL_MAXIMUM_WAIT_MS: number = 10 * 60_000

const MAXIMUM_CONSECUTIVE_FACEBOOK_READ_FAILURES: number = 3

/**
 * Pause for a while.
 * @param milliseconds - How long to wait.
 * @returns A promise resolved once the delay elapsed.
 */
function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve: () => void): void => {
    setTimeout(resolve, milliseconds)
  })
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useProspectSearchStore = defineStore('prospectSearch', () => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()

  const currentSearch: Ref<ProspectSearchDetail | null> = ref(null)
  const recentSearches: Ref<ProspectSearchSummary[]> = ref([])
  const tradeOptions: Ref<ProspectSearchTradeOption[]> = ref([])
  const isStarting: Ref<boolean> = ref(false)
  const isCancelling: Ref<boolean> = ref(false)
  const isResuming: Ref<boolean> = ref(false)
  const loadingSearchId: Ref<number | null> = ref(null)
  const busyCandidateIds: Ref<number[]> = ref([])
  const facebookReading: Ref<ProspectSearchFacebookReading | null> = ref(null)
  const canReadFacebookPagesLocally: Ref<boolean> = ref(false)
  const prospectsCreatedSignal: Ref<number> = ref(0)

  const postedFacebookCandidateIds: Set<number> = new Set()
  const failedFacebookCandidateIds: Set<number> = new Set()
  let pollTimer: ReturnType<typeof setTimeout> | null = null
  let appliedSearchRevision: number = 0
  let isReadingFacebookPages: boolean = false
  let stoppedFacebookReadingSearchId: number | null = null

  const isCurrentSearchActive: ComputedRef<boolean> = computed(
    (): boolean => currentSearch.value !== null && ProspectSearches.isActive(currentSearch.value.status),
  )

  const waitingFacebookPageCount: ComputedRef<number> = computed(
    (): number =>
      currentSearch.value?.candidates.filter(
        (candidate: ProspectSearchCandidate): boolean => candidate.status === 'needs_browser',
      ).length ?? 0,
  )

  /** Stop the pending poll. */
  function stopPolling(): void {
    if (pollTimer !== null) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  /** Plan the next poll of the followed search, while it is still moving. */
  function schedulePoll(): void {
    stopPolling()
    const search: ProspectSearchDetail | null = currentSearch.value
    if (search === null || !ProspectSearches.isActive(search.status) || !userStore.token) return
    const isWaitingForAnotherDevice: boolean = search.status === 'waiting_browser' && !canReadFacebookPagesLocally.value
    pollTimer = setTimeout(
      (): void => {
        pollTimer = null
        refreshCurrentSearch()
      },
      isWaitingForAnotherDevice ? WAITING_FOR_DESKTOP_POLL_INTERVAL_MS : POLL_INTERVAL_MS,
    )
  }

  /**
   * Keep the recent list in step with a search, without fetching the list again.
   * @param detail - The search as last known.
   */
  function rememberInRecentSearches(detail: ProspectSearchDetail): void {
    const { journal: _journal, candidates: _candidates, ...summary }: ProspectSearchDetail = detail
    const isListed: boolean = recentSearches.value.some(
      (search: ProspectSearchSummary): boolean => search.id === detail.id,
    )
    recentSearches.value = isListed
      ? recentSearches.value.map(
          (search: ProspectSearchSummary): ProspectSearchSummary => (search.id === detail.id ? summary : search),
        )
      : [summary, ...recentSearches.value].slice(0, RECENT_SEARCHES_LIMIT)
  }

  /**
   * Follow a search: publish it, signal the prospects it created, keep polling and reading while it runs.
   * @param detail - The search as the API returned it, or patched locally.
   */
  function applySearch(detail: ProspectSearchDetail): void {
    const previous: ProspectSearchDetail | null = currentSearch.value
    const hasCreatedProspects: boolean =
      previous !== null &&
      previous.id === detail.id &&
      ProspectSearches.createdProspectCount(detail) > ProspectSearches.createdProspectCount(previous)
    appliedSearchRevision += 1
    currentSearch.value = detail
    rememberInRecentSearches(detail)
    if (hasCreatedProspects) prospectsCreatedSignal.value += 1
    schedulePoll()
    startFacebookReadingIfNeeded()
  }

  /**
   * Publish the answer of an action, unless the user moved on to another search meanwhile.
   * @param detail - The search the action returned.
   */
  function applyIfStillFollowed(detail: ProspectSearchDetail): void {
    if (currentSearch.value?.id === detail.id) {
      applySearch(detail)
      return
    }
    rememberInRecentSearches(detail)
  }

  /**
   * Fetch the followed search again.
   * @returns A promise resolved once the search is refreshed, or the attempt failed.
   */
  async function refreshCurrentSearch(): Promise<void> {
    const search: ProspectSearchDetail | null = currentSearch.value
    if (search === null) return
    const revision: number = appliedSearchRevision
    try {
      const detail: ProspectSearchDetail = await ProspectSearchService.getSearch(search.id)
      if (appliedSearchRevision === revision) {
        applySearch(detail)
        return
      }
    } catch {
      // A failed poll is simply retried at the next tick.
    }
    schedulePoll()
  }

  /**
   * Launch a search from an objective and follow it.
   * @param payload - Trades, country, towns, count per trade and contact channel.
   * @returns A promise resolved once the search is created.
   * @throws Error carrying the API message when the objective is refused.
   */
  async function startSearch(payload: ProspectSearchCreatePayload): Promise<void> {
    isStarting.value = true
    try {
      applySearch(await ProspectSearchService.createSearch(payload))
    } finally {
      isStarting.value = false
    }
  }

  /**
   * Stop the followed search; what it found is kept.
   * @returns A promise resolved once the search is stopped.
   */
  async function cancelSearch(): Promise<void> {
    const search: ProspectSearchDetail | null = currentSearch.value
    if (search === null || !ProspectSearches.isActive(search.status) || isCancelling.value) return
    isCancelling.value = true
    try {
      const stopped: ProspectSearchDetail = await ProspectSearchService.cancelSearch(search.id)
      if (isReadingFacebookPages && facebookReading.value?.searchId === search.id) {
        stoppedFacebookReadingSearchId = search.id
      }
      applyIfStillFollowed(stopped)
    } finally {
      isCancelling.value = false
    }
  }

  /**
   * Carry on the followed search when it stopped short of its objective.
   * @returns A promise resolved once the search runs again.
   */
  async function resumeSearch(): Promise<void> {
    const search: ProspectSearchDetail | null = currentSearch.value
    if (search === null || isResuming.value) return
    isResuming.value = true
    try {
      const resumed: ProspectSearchDetail = await ProspectSearchService.resumeSearch(search.id)
      if (stoppedFacebookReadingSearchId === search.id) stoppedFacebookReadingSearchId = null
      if (facebookReading.value?.searchId === search.id && !facebookReading.value.isRunning) {
        facebookReading.value = null
      }
      applyIfStillFollowed(resumed)
    } finally {
      isResuming.value = false
    }
  }

  /**
   * Follow another search of the recent list.
   * @param searchId - Identifier of the search to load.
   * @returns A promise resolved once the search is loaded.
   */
  async function loadSearch(searchId: number): Promise<void> {
    loadingSearchId.value = searchId
    try {
      const detail: ProspectSearchDetail = await ProspectSearchService.getSearch(searchId)
      if (loadingSearchId.value === searchId) applySearch(detail)
    } finally {
      if (loadingSearchId.value === searchId) loadingSearchId.value = null
    }
  }

  /**
   * Load the recent searches and, when none is followed yet, follow the one still running, else the latest.
   * @returns A promise resolved once the list (and the followed search, if any) is loaded.
   */
  async function restoreLatestSearch(): Promise<void> {
    recentSearches.value = await ProspectSearchService.listSearches()
    if (currentSearch.value !== null) return
    const latest: ProspectSearchSummary | undefined =
      recentSearches.value.find((search: ProspectSearchSummary): boolean => ProspectSearches.isActive(search.status)) ??
      recentSearches.value[0]
    if (latest) await loadSearch(latest.id)
  }

  /**
   * Load the trades the search recognises, once.
   * @returns A promise resolved once the suggestions are loaded, or the attempt failed.
   */
  async function loadTradeOptions(): Promise<void> {
    if (tradeOptions.value.length > 0) return
    try {
      tradeOptions.value = await ProspectSearchService.listTrades()
    } catch {
      tradeOptions.value = []
    }
  }

  /**
   * Send a manual decision on a candidate, then publish its new place and the refreshed totals.
   * @param candidateId - The candidate decided on.
   * @param sendDecision - The API call carrying the decision, given the search identifier.
   * @returns A promise resolved once the decision is applied.
   */
  async function applyCandidateDecision(
    candidateId: number,
    sendDecision: (searchId: number) => Promise<ProspectSearchCandidate>,
  ): Promise<void> {
    const search: ProspectSearchDetail | null = currentSearch.value
    if (search === null || busyCandidateIds.value.includes(candidateId)) return
    busyCandidateIds.value = [...busyCandidateIds.value, candidateId]
    try {
      const decided: ProspectSearchCandidate = await sendDecision(search.id)
      const followed: ProspectSearchDetail | null = currentSearch.value
      if (followed === null || followed.id !== search.id) return
      applySearch({
        ...followed,
        candidates: followed.candidates.map(
          (candidate: ProspectSearchCandidate): ProspectSearchCandidate =>
            candidate.id === decided.id ? decided : candidate,
        ),
      })
      await refreshCurrentSearch()
    } finally {
      busyCandidateIds.value = busyCandidateIds.value.filter((id: number): boolean => id !== candidateId)
    }
  }

  /**
   * Keep a candidate by hand: it becomes a prospect.
   * @param candidateId - The candidate to keep.
   * @returns A promise resolved once the candidate is kept.
   * @throws Error carrying the API message when the business is already a prospect.
   */
  async function keepCandidate(candidateId: number): Promise<void> {
    await applyCandidateDecision(
      candidateId,
      (searchId: number): Promise<ProspectSearchCandidate> =>
        ProspectSearchService.keepCandidate(searchId, candidateId),
    )
  }

  /**
   * Discard a candidate by hand: no later search proposes it again.
   * @param candidateId - The candidate to discard.
   * @returns A promise resolved once the candidate is discarded.
   * @throws Error carrying the API message when the candidate already became a prospect.
   */
  async function rejectCandidate(candidateId: number): Promise<void> {
    await applyCandidateDecision(
      candidateId,
      (searchId: number): Promise<ProspectSearchCandidate> =>
        ProspectSearchService.rejectCandidate(searchId, candidateId),
    )
  }

  /**
   * Whether the page reading of a search may go on: not stopped by the user, and still running when it is followed.
   * @param searchId - The search whose pages are read.
   * @returns False once the reading has to stop after the page in flight.
   */
  function canKeepReadingFacebookPages(searchId: number): boolean {
    if (stoppedFacebookReadingSearchId === searchId) return false
    const search: ProspectSearchDetail | null = currentSearch.value
    return search === null || search.id !== searchId || ProspectSearches.isActive(search.status)
  }

  /**
   * Wait for the Chrome of this machine, which the local scraper may still be installing on a first launch.
   * @param reading - The reading state, told while Chrome installs.
   * @returns Null once Chrome can be used, or the message explaining why it cannot.
   */
  async function waitForLocalChrome(reading: ProspectSearchFacebookReading): Promise<string | null> {
    let health: ScraperChromeHealth = await getScraperChromeHealth()
    if (health.state === 'unavailable') {
      await requestChromeProvision()
      health = await getScraperChromeHealth()
    }
    if (health.state === 'installing') {
      reading.isChromeInstalling = true
      const deadline: number = Date.now() + CHROME_INSTALL_MAXIMUM_WAIT_MS
      while (health.state === 'installing' && Date.now() < deadline) {
        await wait(CHROME_INSTALL_CHECK_INTERVAL_MS)
        health = await getScraperChromeHealth()
      }
      reading.isChromeInstalling = false
    }
    if (health.state === 'installing') {
      return "Chrome est toujours en cours d'installation sur ce poste. Réessayez dans quelques minutes."
    }
    if (health.state === 'unavailable') {
      const cause: string = health.error ? ` (cause : ${health.error})` : ''
      return `Le téléchargement automatique de Chrome a échoué sur ce poste${cause}. Installez Google Chrome puis réessayez.`
    }
    return null
  }

  /**
   * Read one Facebook page with the local Chrome.
   * @param task - The page to read.
   * @returns What the page publishes, or null when the local scraper failed on it.
   */
  async function readFacebookPage(task: ProspectSearchBrowserTask): Promise<ProspectSearchFacebookContact | null> {
    try {
      return await ProspectSearchService.readFacebookPage(task)
    } catch {
      return null
    }
  }

  /**
   * Read every waiting Facebook page of a search with the local Chrome and hand each result over.
   * @param searchId - The search whose pages are read.
   * @returns A promise resolved once no page is left, or the reading had to stop.
   */
  async function readFacebookPages(searchId: number): Promise<void> {
    isReadingFacebookPages = true
    facebookReading.value = {
      searchId,
      isRunning: true,
      pagesRead: 0,
      pagesToRead: 0,
      currentBusinessName: null,
      isChromeInstalling: false,
      errorMessage: null,
    }
    // Mutate the reactive proxy, never the raw literal: raw mutations would not re-render the banner.
    const reading: ProspectSearchFacebookReading = facebookReading.value
    failedFacebookCandidateIds.clear()
    try {
      reading.errorMessage = await waitForLocalChrome(reading)
      let consecutiveFailureCount: number = 0
      while (reading.errorMessage === null && canKeepReadingFacebookPages(searchId)) {
        const tasks: ProspectSearchBrowserTask[] = (await ProspectSearchService.listBrowserTasks(searchId)).filter(
          (task: ProspectSearchBrowserTask): boolean =>
            !postedFacebookCandidateIds.has(task.candidate_id) && !failedFacebookCandidateIds.has(task.candidate_id),
        )
        if (tasks.length === 0) break
        reading.pagesToRead = reading.pagesRead + tasks.length
        for (const task of tasks) {
          if (!canKeepReadingFacebookPages(searchId)) break
          reading.currentBusinessName = task.name
          const contact: ProspectSearchFacebookContact | null = await readFacebookPage(task)
          reading.pagesRead += 1
          if (contact === null) {
            failedFacebookCandidateIds.add(task.candidate_id)
            consecutiveFailureCount += 1
            if (consecutiveFailureCount >= MAXIMUM_CONSECUTIVE_FACEBOOK_READ_FAILURES) {
              reading.errorMessage = 'Le Chrome de ce poste ne répond plus. Les pages restent en attente.'
              break
            }
            continue
          }
          consecutiveFailureCount = 0
          await ProspectSearchService.recordFacebookContact(searchId, task.candidate_id, contact)
          postedFacebookCandidateIds.add(task.candidate_id)
        }
      }
      if (reading.errorMessage === null && failedFacebookCandidateIds.size > 0) {
        reading.errorMessage =
          failedFacebookCandidateIds.size > 1
            ? `${failedFacebookCandidateIds.size} pages n'ont pas pu être lues sur ce poste. Elles restent en attente.`
            : "1 page n'a pas pu être lue sur ce poste. Elle reste en attente."
      }
    } catch (err: unknown) {
      reading.errorMessage =
        err instanceof Error && err.message ? err.message : 'La lecture des pages Facebook a été interrompue.'
    } finally {
      reading.isRunning = false
      reading.currentBusinessName = null
      isReadingFacebookPages = false
      if (stoppedFacebookReadingSearchId === searchId) stoppedFacebookReadingSearchId = null
    }
    startFacebookReadingIfNeeded()
  }

  /**
   * Start reading the waiting Facebook pages of the followed search, in the desktop app only.
   * @returns A promise resolved once the reading ended, or was not needed.
   */
  async function startFacebookReadingIfNeeded(): Promise<void> {
    const search: ProspectSearchDetail | null = currentSearch.value
    if (search === null) return
    const hasUnreadPage: boolean = search.candidates.some(
      (candidate: ProspectSearchCandidate): boolean =>
        candidate.status === 'needs_browser' &&
        candidate.facebook_url !== null &&
        !postedFacebookCandidateIds.has(candidate.id),
    )
    if (!hasUnreadPage) return
    const hasLocalScraper: boolean = (await getScraperSidecarInfo()) !== null
    if (hasLocalScraper !== canReadFacebookPagesLocally.value) {
      canReadFacebookPagesLocally.value = hasLocalScraper
      schedulePoll()
    }
    if (!hasLocalScraper || isReadingFacebookPages) return
    const followed: ProspectSearchDetail | null = currentSearch.value
    if (followed === null || followed.id !== search.id || !ProspectSearches.isActive(followed.status)) return
    if (facebookReading.value?.searchId === search.id && facebookReading.value.errorMessage !== null) return
    await readFacebookPages(search.id)
  }

  /**
   * Try the Facebook page reading again after it stopped on an error.
   * @returns A promise resolved once the new reading ended.
   */
  async function retryFacebookReading(): Promise<void> {
    if (isReadingFacebookPages) return
    facebookReading.value = null
    await startFacebookReadingIfNeeded()
  }

  /** Forget everything followed. */
  function reset(): void {
    stopPolling()
    appliedSearchRevision += 1
    stoppedFacebookReadingSearchId = isReadingFacebookPages ? (facebookReading.value?.searchId ?? null) : null
    currentSearch.value = null
    recentSearches.value = []
    loadingSearchId.value = null
    busyCandidateIds.value = []
    facebookReading.value = null
  }

  watch(
    (): string | null => userStore.token,
    (token: string | null): void => {
      if (token === null) reset()
    },
  )

  return {
    currentSearch,
    recentSearches,
    tradeOptions,
    isStarting,
    isCancelling,
    isResuming,
    loadingSearchId,
    busyCandidateIds,
    facebookReading,
    canReadFacebookPagesLocally,
    prospectsCreatedSignal,
    isCurrentSearchActive,
    waitingFacebookPageCount,
    startSearch,
    cancelSearch,
    resumeSearch,
    loadSearch,
    restoreLatestSearch,
    loadTradeOptions,
    keepCandidate,
    rejectCandidate,
    retryFacebookReading,
  }
})
