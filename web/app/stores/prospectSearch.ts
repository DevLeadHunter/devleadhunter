/**
 * Shared prospect-search store — the objective-driven search followed by the page, the drawer and the tunnels.
 */
import type { ComputedRef, Ref } from 'vue'
import type { ScraperChromeHealth } from '~/services/scraperSidecarService'
import type { DrawerStackEntry } from '~/types/DrawerStack'
import type {
  ProspectSearchActivity,
  ProspectSearchBrowserTask,
  ProspectSearchCandidate,
  ProspectSearchCreatePayload,
  ProspectSearchDecisionsResult,
  ProspectSearchDetail,
  ProspectSearchFacebookContact,
  ProspectSearchFacebookReading,
  ProspectSearchLeadFilters,
  ProspectSearchRefusedDecision,
  ProspectSearchSummary,
  ProspectSearchTradeCounts,
  ProspectSearchTradeOption,
} from '~/types/ProspectSearch'
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  PROSPECT_SEARCH_MAXIMUM_DECISIONS_PER_REQUEST,
  PROSPECT_SEARCH_MAXIMUM_QUEUED_SEARCHES,
} from '~/constants/prospectSearch'
import { ProspectSearchService } from '~/services/prospectSearchService'
import { getScraperChromeHealth, getScraperSidecarInfo, requestChromeProvision } from '~/services/scraperSidecarService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useUserStore } from '~/stores/user'
import { ProspectSearches } from '~/utils/prospectSearches'

const ACTIVE_SEARCH_POLL_INTERVAL_MS: number = 4_000

const IDLE_POLL_INTERVAL_MS: number = 30_000

const WAITING_FOR_DESKTOP_POLL_INTERVAL_MS: number = 15_000

const REQUESTED_REFRESH_DELAY_MS: number = 300

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
  const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

  const activeSearch: Ref<ProspectSearchSummary | null> = ref(null)
  const queuedSearches: Ref<ProspectSearchSummary[]> = ref([])
  const cancellingQueuedSearchIds: Ref<number[]> = ref([])
  const followedSearch: Ref<ProspectSearchDetail | null> = ref(null)
  const pendingCandidates: Ref<ProspectSearchCandidate[]> = ref([])
  const reportedPendingCount: Ref<number> = ref(0)
  const hasLoadedActivity: Ref<boolean> = ref(false)
  const hasLoadedPendingCandidates: Ref<boolean> = ref(false)
  const isRefreshFailing: Ref<boolean> = ref(false)
  const leadNotifications: Ref<ProspectSearchCandidate[]> = ref([])
  const leadBrowseIds: Ref<number[]> = ref([])
  const isPendingTabDisplayed: Ref<boolean> = ref(false)
  const isPendingTabRequested: Ref<boolean> = ref(false)
  const tradeOptions: Ref<ProspectSearchTradeOption[]> = ref([])
  const isStarting: Ref<boolean> = ref(false)
  const isCancelling: Ref<boolean> = ref(false)
  const isResuming: Ref<boolean> = ref(false)
  const isLoadingFollowedSearch: Ref<boolean> = ref(false)
  const busyCandidateIds: Ref<number[]> = ref([])
  const facebookReading: Ref<ProspectSearchFacebookReading | null> = ref(null)
  const canReadFacebookPagesLocally: Ref<boolean> = ref(false)
  const isDesktopAppOnline: Ref<boolean> = ref(false)
  const prospectsCreatedSignal: Ref<number> = ref(0)

  const knownCandidateIds: Set<number> = new Set()
  const decidedCandidateIds: Set<number> = new Set()
  const postedFacebookCandidateIds: Set<number> = new Set()
  const failedFacebookCandidateIds: Set<number> = new Set()
  let pollTimer: ReturnType<typeof setTimeout> | null = null
  let isWatchingActivity: boolean = false
  let isRefreshingActivity: boolean = false
  let isActivityRefreshRequested: boolean = false
  let stateRevision: number = 0
  let isReadingFacebookPages: boolean = false
  let stoppedFacebookReadingSearchId: number | null = null

  const pendingCount: ComputedRef<number> = computed((): number =>
    hasLoadedPendingCandidates.value ? pendingCandidates.value.length : reportedPendingCount.value,
  )

  const isFollowedSearchActive: ComputedRef<boolean> = computed(
    (): boolean => followedSearch.value !== null && ProspectSearches.isActive(followedSearch.value.status),
  )

  const isSearchRunningOnServer: ComputedRef<boolean> = computed(
    (): boolean => activeSearch.value !== null && ProspectSearches.isRunningOnServer(activeSearch.value.status),
  )

  const isQueueFull: ComputedRef<boolean> = computed(
    (): boolean =>
      isSearchRunningOnServer.value && queuedSearches.value.length >= PROSPECT_SEARCH_MAXIMUM_QUEUED_SEARCHES,
  )

  const latestJournalMessage: ComputedRef<string | null> = computed(
    (): string | null => followedSearch.value?.journal.at(-1)?.message ?? null,
  )

  const waitingFacebookPageCount: ComputedRef<number> = computed(
    (): number =>
      followedSearch.value?.candidates.filter(
        (candidate: ProspectSearchCandidate): boolean => candidate.status === 'needs_browser',
      ).length ?? 0,
  )

  const followedSearchPendingCandidates: ComputedRef<ProspectSearchCandidate[]> = computed(
    (): ProspectSearchCandidate[] => {
      const searchId: number | undefined = followedSearch.value?.id
      return pendingCandidates.value.filter(
        (candidate: ProspectSearchCandidate): boolean => candidate.search_id === searchId,
      )
    },
  )

  const tradeLabels: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
    const labels: Record<string, string> = {}
    tradeOptions.value.forEach((option: ProspectSearchTradeOption): void => {
      labels[option.key] = option.label
    })
    for (const search of [activeSearch.value, followedSearch.value]) {
      search?.trade_counts.forEach((counts: ProspectSearchTradeCounts): void => {
        labels[counts.trade] = counts.label
      })
    }
    return labels
  })

  const isSearchDrawerOpen: ComputedRef<boolean> = computed((): boolean =>
    drawerStack.stack.some((entry: DrawerStackEntry): boolean => entry.kind === 'prospect-search'),
  )

  const canNotifyLeads: ComputedRef<boolean> = computed(
    (): boolean => !isSearchDrawerOpen.value && !isPendingTabDisplayed.value,
  )

  /**
   * Find the catalog label of the trade a lead was searched for.
   * @param candidate - The lead to label.
   * @returns The trade label, or its raw key when no catalog lists it.
   */
  function resolveTradeLabel(candidate: ProspectSearchCandidate): string {
    return tradeLabels.value[candidate.trade] ?? candidate.trade
  }

  /**
   * Build the line shown under a lead's name: its trade, then its town when it is known.
   * @param candidate - The lead to describe.
   * @returns E.g. « Plombier · Rennes ».
   */
  function buildTradeAndTownLabel(candidate: ProspectSearchCandidate): string {
    const tradeLabel: string = resolveTradeLabel(candidate)
    const town: string | null = ProspectSearches.leadTown(candidate)
    return town ? `${tradeLabel} · ${town}` : tradeLabel
  }

  /**
   * List the waiting leads matching what the prospects page filters on: its search box, a town, a trade.
   * @param filters - The text typed in each filter, empty when the filter is unused.
   * @returns The matching leads, newest first.
   */
  function findPendingCandidates(filters: ProspectSearchLeadFilters): ProspectSearchCandidate[] {
    const searchedText: string = filters.searchQuery.trim().toLowerCase()
    const searchedTown: string = filters.town.trim().toLowerCase()
    const searchedTrade: string = filters.trade.trim().toLowerCase()
    return pendingCandidates.value.filter((candidate: ProspectSearchCandidate): boolean => {
      const town: string = (ProspectSearches.leadTown(candidate) ?? '').toLowerCase()
      const trade: string = `${resolveTradeLabel(candidate)} ${candidate.google_category ?? ''}`.toLowerCase()
      const searchableText: string = [candidate.name, town, candidate.email ?? '', candidate.phone ?? '']
        .join(' ')
        .toLowerCase()
      return searchableText.includes(searchedText) && town.includes(searchedTown) && trade.includes(searchedTrade)
    })
  }

  /** Stop the pending poll. */
  function stopPolling(): void {
    if (pollTimer !== null) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  /**
   * Choose how long to wait before the next look at the server.
   * @returns Four seconds while a search runs, thirty otherwise; slower while only another device can move it on.
   */
  function resolvePollDelay(): number {
    const search: ProspectSearchSummary | null = activeSearch.value
    if (search === null) return IDLE_POLL_INTERVAL_MS
    const isWaitingForAnotherDevice: boolean = search.status === 'waiting_browser' && !canReadFacebookPagesLocally.value
    return isWaitingForAnotherDevice ? WAITING_FOR_DESKTOP_POLL_INTERVAL_MS : ACTIVE_SEARCH_POLL_INTERVAL_MS
  }

  /**
   * Plan the next look at the server, while the shell watches and the user is signed in.
   * @param delayMs - Delay before the look; the usual interval when omitted.
   */
  function schedulePoll(delayMs?: number): void {
    stopPolling()
    if (!isWatchingActivity || !userStore.token) return
    pollTimer = setTimeout((): void => {
      pollTimer = null
      refreshActivity()
    }, delayMs ?? resolvePollDelay())
  }

  /** Look at the server again right away, or as soon as the look in flight ends. */
  function requestRefresh(): void {
    if (isRefreshingActivity) {
      isActivityRefreshRequested = true
      return
    }
    schedulePoll(REQUESTED_REFRESH_DELAY_MS)
  }

  /**
   * Publish a search as the followed one, signal the prospects it created, keep reading its Facebook pages.
   * @param detail - The search as the API returned it.
   */
  function applyFollowedSearch(detail: ProspectSearchDetail): void {
    const previous: ProspectSearchDetail | null = followedSearch.value
    const hasCreatedProspects: boolean =
      previous !== null &&
      previous.id === detail.id &&
      ProspectSearches.createdProspectCount(detail) > ProspectSearches.createdProspectCount(previous)
    followedSearch.value = detail
    if (hasCreatedProspects) prospectsCreatedSignal.value += 1
    startFacebookReadingIfNeeded()
  }

  /**
   * Publish the answer of an action on a search (launch, stop, carry on), ahead of the next poll.
   * A search sent to the queue joins it, and leaves the search at work followed.
   * @param detail - The search the action returned.
   */
  function applySearchAction(detail: ProspectSearchDetail): void {
    stateRevision += 1
    const otherQueuedSearches: ProspectSearchSummary[] = queuedSearches.value.filter(
      (search: ProspectSearchSummary): boolean => search.id !== detail.id,
    )
    if (detail.status === 'queued') {
      queuedSearches.value = [...otherQueuedSearches, ProspectSearches.summaryOf(detail)]
      if (followedSearch.value?.id === detail.id) followedSearch.value = detail
    } else {
      queuedSearches.value = otherQueuedSearches
      activeSearch.value = ProspectSearches.isActive(detail.status) ? ProspectSearches.summaryOf(detail) : null
      applyFollowedSearch(detail)
    }
    requestRefresh()
  }

  /**
   * Whether the list of waiting leads no longer matches what the server reports.
   * @returns True when the list has to be fetched again.
   */
  function isPendingListOutdated(): boolean {
    if (!hasLoadedPendingCandidates.value) return true
    if (reportedPendingCount.value !== pendingCandidates.value.length) return true
    const listedIds: Set<number> = new Set(
      pendingCandidates.value.map((candidate: ProspectSearchCandidate): number => candidate.id),
    )
    const followedSearchCandidates: ProspectSearchCandidate[] = followedSearch.value?.candidates ?? []
    const hasUnlistedWaitingLead: boolean = followedSearchCandidates.some(
      (candidate: ProspectSearchCandidate): boolean =>
        candidate.is_pending && !listedIds.has(candidate.id) && !decidedCandidateIds.has(candidate.id),
    )
    return hasUnlistedWaitingLead
  }

  /**
   * Fetch the leads waiting for a decision and queue a notification for each new one.
   * @param revision - State revision the fetch belongs to; a stale answer is dropped.
   * @returns A promise resolved once the list is published.
   */
  async function refreshPendingCandidates(revision: number): Promise<void> {
    const candidates: ProspectSearchCandidate[] = (await ProspectSearchService.listPendingCandidates()).filter(
      (candidate: ProspectSearchCandidate): boolean => !decidedCandidateIds.has(candidate.id),
    )
    if (revision !== stateRevision) return
    const isFirstLoad: boolean = !hasLoadedPendingCandidates.value
    const newCandidatesOldestFirst: ProspectSearchCandidate[] = candidates
      .filter((candidate: ProspectSearchCandidate): boolean => !knownCandidateIds.has(candidate.id))
      .reverse()
    candidates.forEach((candidate: ProspectSearchCandidate): void => {
      knownCandidateIds.add(candidate.id)
    })
    pendingCandidates.value = candidates
    hasLoadedPendingCandidates.value = true
    const pendingIds: Set<number> = new Set(
      candidates.map((candidate: ProspectSearchCandidate): number => candidate.id),
    )
    const notifications: ProspectSearchCandidate[] = leadNotifications.value.filter(
      (candidate: ProspectSearchCandidate): boolean => pendingIds.has(candidate.id),
    )
    const shouldAnnounceNewCandidates: boolean = !isFirstLoad && canNotifyLeads.value
    if (shouldAnnounceNewCandidates) notifications.push(...newCandidatesOldestFirst)
    leadNotifications.value = notifications
  }

  /**
   * Look at the server: the waiting count, the running search, then whatever those two made outdated.
   * @returns A promise resolved once the look ended and the next one is planned.
   */
  async function refreshActivity(): Promise<void> {
    if (isRefreshingActivity || !userStore.token) return
    isRefreshingActivity = true
    stopPolling()
    const revision: number = stateRevision
    try {
      const hasLocalScraper: boolean = (await getScraperSidecarInfo()) !== null
      const activity: ProspectSearchActivity = await ProspectSearchService.getActivity(hasLocalScraper)
      if (revision !== stateRevision) return
      const previousActiveSearchId: number | null = activeSearch.value?.id ?? null
      activeSearch.value = activity.active_search
      queuedSearches.value = activity.queued_searches ?? []
      isDesktopAppOnline.value = activity.is_desktop_app_online ?? false
      reportedPendingCount.value = activity.pending_count
      hasLoadedActivity.value = true
      const justEndedSearchId: number | null = activity.active_search === null ? previousActiveSearchId : null
      const searchIdToRead: number | null = activity.active_search?.id ?? justEndedSearchId
      if (searchIdToRead !== null) {
        const detail: ProspectSearchDetail = await ProspectSearchService.getSearch(searchIdToRead)
        if (revision !== stateRevision) return
        applyFollowedSearch(detail)
      }
      if (isPendingListOutdated()) await refreshPendingCandidates(revision)
      isRefreshFailing.value = false
    } catch {
      if (revision === stateRevision) isRefreshFailing.value = true
    } finally {
      isRefreshingActivity = false
      schedulePoll(isActivityRefreshRequested ? REQUESTED_REFRESH_DELAY_MS : undefined)
      isActivityRefreshRequested = false
    }
  }

  /** Start following the user's searches and waiting leads (called once by the dashboard shell). */
  function startWatching(): void {
    if (isWatchingActivity) return
    isWatchingActivity = true
    loadTradeOptions()
    refreshActivity()
  }

  /** Stop following (the dashboard shell is gone). */
  function stopWatching(): void {
    isWatchingActivity = false
    stopPolling()
  }

  /**
   * Launch a search from an objective and follow it, or queue it behind the search at work.
   * @param payload - Trades, country, towns, count per trade, contact channel and validation mode.
   * @returns The created search: running, or queued.
   * @throws Error carrying the API message when the objective is refused or the queue is full.
   */
  async function startSearch(payload: ProspectSearchCreatePayload): Promise<ProspectSearchDetail> {
    isStarting.value = true
    try {
      const created: ProspectSearchDetail = await ProspectSearchService.createSearch(payload)
      applySearchAction(created)
      return created
    } finally {
      isStarting.value = false
    }
  }

  /**
   * Take a search out of the queue before it starts; nothing was searched for it.
   * @param searchId - The queued search.
   * @returns A promise resolved once the search left the queue.
   * @throws Error carrying the API message when the search could not be taken out.
   */
  async function cancelQueuedSearch(searchId: number): Promise<void> {
    if (cancellingQueuedSearchIds.value.includes(searchId)) return
    cancellingQueuedSearchIds.value = [...cancellingQueuedSearchIds.value, searchId]
    try {
      await ProspectSearchService.cancelSearch(searchId)
      stateRevision += 1
      queuedSearches.value = queuedSearches.value.filter(
        (search: ProspectSearchSummary): boolean => search.id !== searchId,
      )
      requestRefresh()
    } finally {
      cancellingQueuedSearchIds.value = cancellingQueuedSearchIds.value.filter((id: number): boolean => id !== searchId)
    }
  }

  /**
   * Stop the running search; what it found is kept.
   * @returns A promise resolved once the search is stopped.
   */
  async function cancelSearch(): Promise<void> {
    const searchId: number | null = activeSearch.value?.id ?? null
    if (searchId === null || isCancelling.value) return
    isCancelling.value = true
    try {
      const stopped: ProspectSearchDetail = await ProspectSearchService.cancelSearch(searchId)
      if (isReadingFacebookPages && facebookReading.value?.searchId === searchId) {
        stoppedFacebookReadingSearchId = searchId
      }
      applySearchAction(stopped)
    } finally {
      isCancelling.value = false
    }
  }

  /**
   * Carry on the followed search when it stopped short of its objective.
   * @returns A promise resolved once the search runs again.
   */
  async function resumeSearch(): Promise<void> {
    const search: ProspectSearchDetail | null = followedSearch.value
    if (search === null || isResuming.value) return
    isResuming.value = true
    try {
      const resumed: ProspectSearchDetail = await ProspectSearchService.resumeSearch(search.id)
      if (stoppedFacebookReadingSearchId === search.id) stoppedFacebookReadingSearchId = null
      if (facebookReading.value?.searchId === search.id && !facebookReading.value.isRunning) {
        facebookReading.value = null
      }
      applySearchAction(resumed)
    } finally {
      isResuming.value = false
    }
  }

  /**
   * Follow the user's latest search when none is followed yet (the drawer was opened with nothing running).
   * @returns A promise resolved once the latest search is loaded, or there is none.
   */
  async function loadLatestSearch(): Promise<void> {
    if (followedSearch.value !== null || isLoadingFollowedSearch.value) return
    isLoadingFollowedSearch.value = true
    const revision: number = stateRevision
    try {
      const searches: ProspectSearchSummary[] = await ProspectSearchService.listSearches()
      const latest: ProspectSearchSummary | undefined =
        searches.find((search: ProspectSearchSummary): boolean => ProspectSearches.isActive(search.status)) ??
        searches[0]
      if (!latest || revision !== stateRevision || followedSearch.value !== null) return
      const detail: ProspectSearchDetail = await ProspectSearchService.getSearch(latest.id)
      if (revision === stateRevision && followedSearch.value === null) applyFollowedSearch(detail)
    } finally {
      isLoadingFollowedSearch.value = false
    }
  }

  /**
   * Load the trades the search recognises, once.
   * @returns A promise resolved once the catalog is loaded, or the attempt failed.
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
   * Take decided leads out of everything that lists the waiting ones.
   * @param candidateIds - The leads that no longer wait.
   */
  function removePendingCandidates(candidateIds: number[]): void {
    const removedIds: Set<number> = new Set(candidateIds)
    const stillPending: ProspectSearchCandidate[] = pendingCandidates.value.filter(
      (candidate: ProspectSearchCandidate): boolean => !removedIds.has(candidate.id),
    )
    const removedCount: number = pendingCandidates.value.length - stillPending.length
    reportedPendingCount.value = Math.max(0, reportedPendingCount.value - removedCount)
    pendingCandidates.value = stillPending
    leadNotifications.value = leadNotifications.value.filter(
      (candidate: ProspectSearchCandidate): boolean => !removedIds.has(candidate.id),
    )
  }

  /**
   * Mark leads as being decided on, or release them.
   * @param candidateIds - The leads concerned.
   * @param isBusy - True while their decision is in flight.
   */
  function setCandidatesBusy(candidateIds: number[], isBusy: boolean): void {
    const withoutThem: number[] = busyCandidateIds.value.filter((id: number): boolean => !candidateIds.includes(id))
    busyCandidateIds.value = isBusy ? [...withoutThem, ...candidateIds] : withoutThem
  }

  /**
   * Send the decision taken on one lead, then take it out of the waiting ones.
   * @param candidate - The lead decided on.
   * @param sendDecision - The API call carrying the decision.
   * @param createsProspect - Whether the decision turns the lead into a prospect.
   * @returns True once the decision is applied, false when another decision on this lead is already in flight.
   * @throws Error carrying the API message when the decision is refused.
   */
  async function applyDecision(
    candidate: ProspectSearchCandidate,
    sendDecision: () => Promise<ProspectSearchCandidate>,
    createsProspect: boolean,
  ): Promise<boolean> {
    if (busyCandidateIds.value.includes(candidate.id)) return false
    setCandidatesBusy([candidate.id], true)
    decidedCandidateIds.add(candidate.id)
    try {
      await sendDecision()
      removePendingCandidates([candidate.id])
      if (createsProspect) prospectsCreatedSignal.value += 1
      return true
    } catch (err: unknown) {
      decidedCandidateIds.delete(candidate.id)
      throw err
    } finally {
      setCandidatesBusy([candidate.id], false)
      requestRefresh()
    }
  }

  /**
   * Accept a lead: it becomes a prospect.
   * @param candidate - The lead to accept.
   * @returns True once the lead is a prospect, false when a decision on it was already in flight.
   * @throws Error carrying the API message when the business is already a prospect.
   */
  async function acceptCandidate(candidate: ProspectSearchCandidate): Promise<boolean> {
    return applyDecision(
      candidate,
      (): Promise<ProspectSearchCandidate> => ProspectSearchService.keepCandidate(candidate.search_id, candidate.id),
      true,
    )
  }

  /**
   * Refuse a lead: no later search proposes it again.
   * @param candidate - The lead to refuse.
   * @returns True once the lead is refused, false when a decision on it was already in flight.
   * @throws Error carrying the API message when the lead already became a prospect.
   */
  async function rejectCandidate(candidate: ProspectSearchCandidate): Promise<boolean> {
    return applyDecision(
      candidate,
      (): Promise<ProspectSearchCandidate> => ProspectSearchService.rejectCandidate(candidate.search_id, candidate.id),
      false,
    )
  }

  /**
   * Send decisions through the bulk route, a hundred leads at most per request, and add the answers up.
   * @param acceptedCandidateIds - Leads to accept.
   * @param rejectedCandidateIds - Leads to refuse.
   * @returns How many decisions were applied, and the ones the server refused.
   * @throws Error carrying the API message when a request is refused as a whole.
   */
  async function sendDecisions(
    acceptedCandidateIds: number[],
    rejectedCandidateIds: number[],
  ): Promise<ProspectSearchDecisionsResult> {
    const total: ProspectSearchDecisionsResult = { accepted: 0, rejected: 0, refused: [] }
    const acceptedIds: Set<number> = new Set(acceptedCandidateIds)
    const candidateIds: number[] = [...acceptedCandidateIds, ...rejectedCandidateIds]
    for (let start: number = 0; start < candidateIds.length; start += PROSPECT_SEARCH_MAXIMUM_DECISIONS_PER_REQUEST) {
      const batch: number[] = candidateIds.slice(start, start + PROSPECT_SEARCH_MAXIMUM_DECISIONS_PER_REQUEST)
      const result: ProspectSearchDecisionsResult = await ProspectSearchService.decideCandidates({
        accept: batch.filter((id: number): boolean => acceptedIds.has(id)),
        reject: batch.filter((id: number): boolean => !acceptedIds.has(id)),
      })
      total.accepted += result.accepted
      total.rejected += result.rejected
      total.refused.push(...result.refused)
    }
    return total
  }

  /**
   * Accept and refuse several leads at once.
   * @param acceptedCandidateIds - Leads to accept.
   * @param rejectedCandidateIds - Leads to refuse.
   * @returns How many decisions were applied, and the ones the server refused.
   * @throws Error carrying the API message when the whole request is refused.
   */
  async function decideCandidates(
    acceptedCandidateIds: number[],
    rejectedCandidateIds: number[],
  ): Promise<ProspectSearchDecisionsResult> {
    const candidateIds: number[] = [...acceptedCandidateIds, ...rejectedCandidateIds]
    setCandidatesBusy(candidateIds, true)
    candidateIds.forEach((id: number): void => {
      decidedCandidateIds.add(id)
    })
    try {
      const result: ProspectSearchDecisionsResult = await sendDecisions(acceptedCandidateIds, rejectedCandidateIds)
      const refusedIds: Set<number> = new Set(
        result.refused.map((refusal: ProspectSearchRefusedDecision): number => refusal.candidate_id),
      )
      refusedIds.forEach((id: number): void => {
        decidedCandidateIds.delete(id)
      })
      removePendingCandidates(candidateIds.filter((id: number): boolean => !refusedIds.has(id)))
      if (result.accepted > 0) prospectsCreatedSignal.value += 1
      return result
    } catch (err: unknown) {
      candidateIds.forEach((id: number): void => {
        decidedCandidateIds.delete(id)
      })
      throw err
    } finally {
      setCandidatesBusy(candidateIds, false)
      requestRefresh()
    }
  }

  /**
   * Take back a refusal: the leads wait for a decision again.
   * @param candidates - The leads refused a moment ago.
   * @returns How many of them are waiting again.
   */
  async function restoreRefusedCandidates(candidates: ProspectSearchCandidate[]): Promise<number> {
    const results: PromiseSettledResult<ProspectSearchCandidate>[] = await Promise.allSettled(
      candidates.map(
        (candidate: ProspectSearchCandidate): Promise<ProspectSearchCandidate> =>
          ProspectSearchService.restoreCandidate(candidate.search_id, candidate.id),
      ),
    )
    const restoredIds: number[] = results.flatMap((result: PromiseSettledResult<ProspectSearchCandidate>): number[] =>
      result.status === 'fulfilled' ? [result.value.id] : [],
    )
    restoredIds.forEach((id: number): void => {
      decidedCandidateIds.delete(id)
    })
    stateRevision += 1
    hasLoadedPendingCandidates.value = false
    requestRefresh()
    return restoredIds.length
  }

  /**
   * Take a lead notification off the screen.
   * @param candidateId - The lead the notification announces.
   */
  function dismissLeadNotification(candidateId: number): void {
    leadNotifications.value = leadNotifications.value.filter(
      (candidate: ProspectSearchCandidate): boolean => candidate.id !== candidateId,
    )
  }

  /**
   * Remember the list the lead drawer walks through, in the order its opener displays it.
   * @param candidateIds - Leads in display order.
   */
  function setLeadBrowseList(candidateIds: number[]): void {
    leadBrowseIds.value = candidateIds
  }

  /**
   * Tell whether the « À valider » tab is on screen: new leads then land in it, without a notification.
   * @param isDisplayed - True while the tab is the one shown.
   */
  function setPendingTabDisplayed(isDisplayed: boolean): void {
    isPendingTabDisplayed.value = isDisplayed
  }

  /** Ask the prospects page to show its « À valider » tab, now or as soon as it opens. */
  function requestPendingTab(): void {
    isPendingTabRequested.value = true
  }

  /**
   * Read the request for the « À valider » tab, and clear it.
   * @returns True when the tab was asked for.
   */
  function consumePendingTabRequest(): boolean {
    const wasRequested: boolean = isPendingTabRequested.value
    isPendingTabRequested.value = false
    return wasRequested
  }

  /**
   * Whether the page reading of a search may go on: not stopped by the user, and still running when it is followed.
   * @param searchId - The search whose pages are read.
   * @returns False once the reading has to stop after the page in flight.
   */
  function canKeepReadingFacebookPages(searchId: number): boolean {
    if (stoppedFacebookReadingSearchId === searchId) return false
    const search: ProspectSearchDetail | null = followedSearch.value
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
    const search: ProspectSearchDetail | null = followedSearch.value
    if (search === null) return
    const hasUnreadPage: boolean = search.candidates.some(
      (candidate: ProspectSearchCandidate): boolean =>
        candidate.status === 'needs_browser' &&
        candidate.facebook_url !== null &&
        !postedFacebookCandidateIds.has(candidate.id),
    )
    if (!hasUnreadPage) return
    const hasLocalScraper: boolean = (await getScraperSidecarInfo()) !== null
    canReadFacebookPagesLocally.value = hasLocalScraper
    if (!hasLocalScraper || isReadingFacebookPages) return
    const followed: ProspectSearchDetail | null = followedSearch.value
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

  /** Forget everything followed (the user signed out). */
  function reset(): void {
    stopPolling()
    stateRevision += 1
    stoppedFacebookReadingSearchId = isReadingFacebookPages ? (facebookReading.value?.searchId ?? null) : null
    activeSearch.value = null
    queuedSearches.value = []
    cancellingQueuedSearchIds.value = []
    followedSearch.value = null
    pendingCandidates.value = []
    reportedPendingCount.value = 0
    hasLoadedActivity.value = false
    hasLoadedPendingCandidates.value = false
    isRefreshFailing.value = false
    leadNotifications.value = []
    leadBrowseIds.value = []
    isPendingTabRequested.value = false
    busyCandidateIds.value = []
    facebookReading.value = null
    isDesktopAppOnline.value = false
    knownCandidateIds.clear()
    decidedCandidateIds.clear()
  }

  watch(
    (): string | null => userStore.token,
    (token: string | null): void => {
      if (token === null) {
        reset()
        return
      }
      if (isWatchingActivity) {
        loadTradeOptions()
        schedulePoll(0)
      }
    },
  )

  watch(canNotifyLeads, (canNotify: boolean): void => {
    if (!canNotify) leadNotifications.value = []
  })

  return {
    activeSearch,
    queuedSearches,
    cancellingQueuedSearchIds,
    isQueueFull,
    followedSearch,
    pendingCandidates,
    pendingCount,
    hasLoadedActivity,
    hasLoadedPendingCandidates,
    isRefreshFailing,
    leadNotifications,
    leadBrowseIds,
    isPendingTabRequested,
    tradeOptions,
    isStarting,
    isCancelling,
    isResuming,
    isLoadingFollowedSearch,
    busyCandidateIds,
    facebookReading,
    canReadFacebookPagesLocally,
    isDesktopAppOnline,
    prospectsCreatedSignal,
    isFollowedSearchActive,
    isSearchRunningOnServer,
    latestJournalMessage,
    waitingFacebookPageCount,
    followedSearchPendingCandidates,
    resolveTradeLabel,
    buildTradeAndTownLabel,
    findPendingCandidates,
    startWatching,
    stopWatching,
    startSearch,
    cancelSearch,
    cancelQueuedSearch,
    resumeSearch,
    loadLatestSearch,
    loadTradeOptions,
    acceptCandidate,
    rejectCandidate,
    decideCandidates,
    restoreRefusedCandidates,
    dismissLeadNotification,
    setLeadBrowseList,
    setPendingTabDisplayed,
    requestPendingTab,
    consumePendingTabRequest,
    retryFacebookReading,
  }
})
