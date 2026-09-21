import type { UseScrapingJobStreamReturn } from '~/types/Composables'
/** Shared prospect-search store — one scraping job lifecycle for drawer + results page. */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useRuntimeConfig } from '#app'
import { useUserStore } from '~/stores/user'
import { useScrapingJobStream } from '~/composables/useScrapingJobStream'
import type { ScrapingJobProgressState } from '~/composables/useScrapingJobStream'
import type { Prospect, ProspectCountry } from '~/types'
import { EnrichmentService } from '~/services/enrichmentService'
import type { ProspectEnrichment } from '~/services/enrichmentService'
import { ProspectsService } from '~/services/prospectsService'
import { getScraperChromeHealth, getScraperSidecarInfo, requestChromeProvision } from '~/services/scraperSidecarService'
import type { ScraperChromeHealth, ScraperSidecarInfo } from '~/services/scraperSidecarService'

/** A scraping job as returned by the API. */
export type ScrapingJob = {
  id: string
  user_id: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  category: string | null
  city: string | null
  country: ProspectCountry
  max_results: number
  source: string | null
  skip_duplicates: boolean
  only_without_website: boolean
  progress: ScrapingJobProgressState
  logs?: string[]
  live_prospects?: Prospect[]
  results: number[]
  skipped_duplicates: number
  known_pages_skipped: number
  parent_job_id?: string | null
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

/** Parameters for starting a search. */
export type ProspectSearchParams = {
  category: string
  city: string
  country: ProspectCountry
  maxResults: number
  source: string
  skipDuplicates: boolean
  onlyWithoutWebsite: boolean
}

/** Progress of the enrich-and-match loop chained after a Facebook search. */
export type FacebookAutoEnrichState = {
  running: boolean
  /** Search round in progress (each round is one discovery job digging deeper). */
  round: number
  /** Candidate pages enriched so far, across every round. */
  tested: number
  /** Usable prospects kept — email present, website per the checkbox. */
  kept: number
  /** Matches asked by the user (the search form's max results). */
  needed: number
  /** Pages rejected and excluded because they expose no contact email. */
  rejectedNoEmail: number
  /** Pages rejected and excluded because the business has a real website. */
  rejectedWebsite: number
  /** Candidates whose enrichment failed — removed but NOT excluded (retryable later). */
  failed: number
  /** Last enrichment failure message — surfaces WHY pages were unreadable. */
  lastFailure: string | null
  /** Pages skipped because previous searches already tested and rejected them. */
  knownSkipped: number
  /** 1-based index of the page being verified in the current round (0 = none yet). */
  checking: number
  /** Number of candidate pages in the current round. */
  roundSize: number
  /** Chrome is being installed by the sidecar (first launch on this machine). */
  chromeInstalling: boolean
  /** The source dried up (or the round cap was hit) before reaching `needed`. */
  exhausted: boolean
  error: string | null
}

/** Search rounds the Facebook match loop launches before giving up. */
export const FACEBOOK_MAX_ROUNDS: number = 4

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useProspectSearchStore = defineStore('prospectSearch', () => {
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const stream: UseScrapingJobStreamReturn = useScrapingJobStream()

  const currentJob: Ref<ScrapingJob | null> = ref(null)
  const recentJobs: Ref<ScrapingJob[]> = ref([])
  const isStarting: Ref<boolean> = ref(false)
  const isCancelling: Ref<boolean> = ref(false)
  const isRefreshing: Ref<boolean> = ref(false)
  const completedSignal: Ref<number> = ref(0)
  const autoEnrich: Ref<FacebookAutoEnrichState | null> = ref(null)
  /** The usable prospects the Facebook match loop kept — the only ones the user sees. */
  const facebookKeptProspects: Ref<Prospect[]> = ref([])
  /** Jobs whose chained enrichment already ran — completion is signalled twice (stream + poll). */
  const autoEnrichedJobIds: Set<string> = new Set()
  /** Jobs launched BY the match loop as extra rounds — they continue the running state. */
  const facebookRoundJobIds: Set<string> = new Set()

  let pollInterval: ReturnType<typeof setInterval> | null = null

  const liveProgress: ComputedRef<ScrapingJobProgressState> = computed((): ScrapingJobProgressState => {
    if (stream.progress.value.total > 0 || stream.progress.value.current > 0) return stream.progress.value
    return currentJob.value?.progress ?? stream.progress.value
  })
  const streamLogs: ComputedRef<string[]> = computed((): string[] => stream.logs.value)
  const streamProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => stream.prospects.value)
  const streamConnected: ComputedRef<boolean> = computed((): boolean => stream.isConnected.value)
  const streamSkipped: ComputedRef<number> = computed((): number => stream.skippedDuplicates.value)

  const isSearching: ComputedRef<boolean> = computed(
    (): boolean => currentJob.value?.status === 'running' || currentJob.value?.status === 'pending',
  )

  /**
   * User-facing progress. A Facebook search is measured in USABLE prospects kept by
   * the match loop against the count asked — never in internal candidates.
   */
  const displayProgress: ComputedRef<ScrapingJobProgressState> = computed((): ScrapingJobProgressState => {
    const job: ScrapingJob | null = currentJob.value
    if (job?.source === 'facebook') {
      const needed: number = autoEnrich.value?.needed ?? job.max_results
      const kept: number = autoEnrich.value?.kept ?? 0
      return {
        current: kept,
        total: needed,
        percentage: needed > 0 ? Math.min(100, (kept / needed) * 100) : 0,
        current_prospect: null,
        estimated_time_remaining: null,
      }
    }
    return liveProgress.value
  })

  /**
   * Build the auth header from the user's token.
   * @returns The Authorization header (empty when unauthenticated).
   */
  function authHeaders(): Record<string, string> {
    return userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}
  }

  /** Stop the background poll. */
  function stopPolling(): void {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  /** Start polling the current job's status. */
  function startPolling(): void {
    stopPolling()
    pollInterval = setInterval((): void => {
      void refreshJobStatus()
    }, 8000)
  }

  /**
   * Hydrate + connect the live stream for a job.
   * @param job - The job to stream.
   */
  function attachStream(job: ScrapingJob): void {
    stream.hydrateFromJob({
      logs: job.logs,
      live_prospects: job.live_prospects,
      progress: job.progress,
      skipped_duplicates: job.skipped_duplicates,
    })
    if (!userStore.token) return
    stream.connect(job.id, userStore.token, {
      onDone: async (summary: { skipped_duplicates: number }): Promise<void> => {
        stopPolling()
        stream.disconnect()
        await refreshJobStatus()
        if (currentJob.value) {
          currentJob.value.status = 'completed'
          currentJob.value.skipped_duplicates = summary.skipped_duplicates
        }
        completedSignal.value += 1
        if (currentJob.value) void maybeAutoEnrichFacebook(currentJob.value)
      },
      onCancelled: async (): Promise<void> => {
        stopPolling()
        stream.disconnect()
        await refreshJobStatus()
        if (currentJob.value) currentJob.value.status = 'cancelled'
        isCancelling.value = false
      },
      onError: async (): Promise<void> => {
        stopPolling()
        await refreshJobStatus()
        isCancelling.value = false
      },
    })
  }

  /**
   * Remove untested candidate prospects (no exclusion) so nothing unusable lingers
   * when the match loop cannot run — the pages stay rediscoverable later.
   * @param candidates - The candidates to remove.
   * @returns A promise resolved once they are gone.
   */
  async function discardCandidates(candidates: Prospect[]): Promise<void> {
    for (const candidate of candidates) {
      try {
        await ProspectsService.deleteProspect(candidate.id)
      } catch {
        // Non-critical: an extra empty prospect is annoying but harmless.
      }
    }
  }

  /**
   * Chain the local enrich-and-match LOOP right after a Facebook search completes.
   *
   * Facebook discovery only yields name + city + page URL (the SERP carries no
   * contact data) — the base fields live on the Facebook page itself, which only
   * the desktop sidecar can read (logged-out, residential IP). Each round enriches
   * the round's candidates one by one and keeps only usable matches — email
   * present, and no website when the search asked for site-less prospects. A
   * rejected page is deleted AND excluded server-side, so when the round ends
   * short of the asked count, the loop relaunches the same search: discovery then
   * skips every tested page and digs into deeper SERP pages for new candidates.
   * The loop ends when the asked count is reached, a round finds no new candidate
   * (source dry), or the round cap is hit.
   * @param job - The job that just completed (a user search or a loop round).
   * @returns A promise resolved once this round is processed.
   */
  async function maybeAutoEnrichFacebook(job: ScrapingJob): Promise<void> {
    if (job.source !== 'facebook' || autoEnrichedJobIds.has(job.id)) return
    autoEnrichedJobIds.add(job.id)

    let state: FacebookAutoEnrichState
    if (facebookRoundJobIds.has(job.id) && autoEnrich.value) {
      state = autoEnrich.value
      state.round += 1
    } else {
      autoEnrich.value = {
        running: true,
        round: 1,
        tested: 0,
        kept: 0,
        needed: job.max_results,
        rejectedNoEmail: 0,
        rejectedWebsite: 0,
        failed: 0,
        lastFailure: null,
        knownSkipped: 0,
        checking: 0,
        roundSize: 0,
        chromeInstalling: false,
        exhausted: false,
        error: null,
      }
      // Mutate the REACTIVE proxy, never the raw literal: raw mutations update the
      // data without triggering a re-render, freezing the banner mid-verification.
      state = autoEnrich.value
      facebookKeptProspects.value = []
    }
    state.knownSkipped += job.known_pages_skipped ?? 0

    const candidates: Prospect[] = (job.live_prospects ?? []).filter((prospect: Prospect): boolean =>
      Boolean(prospect.facebook_url),
    )
    if (candidates.length === 0) {
      // Discovery dug as deep as it could and surfaced nothing new — the source is dry.
      state.exhausted = state.kept < state.needed
      state.running = false
      return
    }

    const sidecar: ScraperSidecarInfo | null = await getScraperSidecarInfo()
    if (!sidecar) {
      state.running = false
      state.error =
        "La lecture des pages Facebook s'exécute en local — relancez la recherche depuis l'application desktop."
      await discardCandidates(candidates)
      return
    }

    // First launch on a new machine: the sidecar may still be downloading its Chrome
    // (~150 MB). Wait for it instead of failing every page — plug-and-play. A failed
    // startup download is retried on demand here, so a transient network refusal
    // never requires an app restart.
    let health: ScraperChromeHealth = await getScraperChromeHealth()
    if (health.state === 'unavailable') {
      await requestChromeProvision()
      health = await getScraperChromeHealth()
    }
    if (health.state === 'installing') {
      state.chromeInstalling = true
      const deadline: number = Date.now() + 10 * 60_000
      while (health.state === 'installing' && Date.now() < deadline) {
        await new Promise(
          (resolve: (value: unknown) => void): ReturnType<typeof setTimeout> => setTimeout(resolve, 10_000),
        )
        health = await getScraperChromeHealth()
      }
      state.chromeInstalling = false
    }
    if (health.state === 'installing' || health.state === 'unavailable') {
      state.running = false
      state.error =
        health.state === 'installing'
          ? "Chrome est toujours en cours d'installation sur ce poste — relancez la recherche dans quelques minutes."
          : `Le téléchargement automatique de Chrome a échoué sur ce poste${
              health.error ? ` (cause : ${health.error})` : ''
            }. Installez Google Chrome puis relancez la recherche.`
      await discardCandidates(candidates)
      return
    }

    state.checking = 0
    state.roundSize = candidates.length
    const testedBefore: number = state.tested
    const failedBefore: number = state.failed
    for (const candidate of candidates) {
      state.checking += 1
      if (state.kept >= state.needed) {
        // Surplus candidate, never tested — removed; a future search can rediscover it.
        try {
          await ProspectsService.deleteProspect(candidate.id)
        } catch {
          // Non-critical: an extra empty prospect is annoying but harmless.
        }
        continue
      }
      try {
        const record: ProspectEnrichment = await EnrichmentService.runProspectEnrichment(
          candidate.id,
          candidate.name,
          candidate.city ?? '',
          candidate.google_maps_url ?? '',
          candidate.facebook_url ?? '',
        )
        state.tested += 1
        if (record.status !== 'completed') {
          // Scrape failed — no data to judge, so the empty candidate is removed rather
          // than left as an unusable prospect. NOT excluded: a later round can retry it.
          state.failed += 1
          state.lastFailure = record.error_message ?? state.lastFailure
          try {
            await ProspectsService.deleteProspect(candidate.id)
          } catch {
            // Non-critical.
          }
          continue
        }
        const fresh: Prospect = await ProspectsService.getProspect(candidate.id)
        const usable: boolean = Boolean(fresh.email) && (!job.only_without_website || !fresh.website)
        if (usable) {
          state.kept += 1
          facebookKeptProspects.value.push(fresh)
        } else {
          if (fresh.email) {
            state.rejectedWebsite += 1
          } else {
            state.rejectedNoEmail += 1
          }
          await ProspectsService.deleteProspect(candidate.id)
          await ProspectsService.excludeFacebookPage(
            candidate.facebook_url ?? '',
            fresh.email ? 'has_website' : 'no_email',
          )
        }
      } catch (err: unknown) {
        state.failed += 1
        if (err instanceof Error && err.message) state.lastFailure = err.message
        try {
          await ProspectsService.deleteProspect(candidate.id)
        } catch {
          // Non-critical.
        }
      }
    }

    if (state.kept >= state.needed) {
      state.running = false
      return
    }
    const roundTested: number = state.tested - testedBefore
    const roundFailed: number = state.failed - failedBefore
    if (roundTested > 0 && roundFailed >= roundTested) {
      // The whole round failed to enrich — relaunching would rediscover and re-fail the
      // same pages (failures are not excluded). Stop and surface the breakage instead.
      state.running = false
      state.error = 'Tous les enrichissements du round ont échoué — vérifiez Chrome et relancez la recherche.'
      return
    }
    if (state.round >= FACEBOOK_MAX_ROUNDS) {
      state.exhausted = true
      state.running = false
      return
    }
    // Every tested page is now excluded server-side — the next round digs deeper.
    try {
      const next: ScrapingJob = await launchJob({
        category: job.category,
        city: job.city,
        country: job.country,
        max_results: state.needed - state.kept,
        source: 'facebook',
        skip_duplicates: job.skip_duplicates,
        only_without_website: job.only_without_website,
        // Rounds all point at the user's ORIGINAL search — one search, one row.
        parent_job_id: job.parent_job_id ?? job.id,
      })
      facebookRoundJobIds.add(next.id)
    } catch (err: unknown) {
      state.running = false
      state.error = err instanceof Error ? err.message : 'Relance de la recherche impossible.'
    }
  }

  /**
   * Refresh the current job's status from the API.
   * @returns A promise resolved once refreshed.
   */
  async function refreshJobStatus(): Promise<void> {
    if (!currentJob.value) return
    try {
      isRefreshing.value = true
      const response: ScrapingJob = await $fetch<ScrapingJob>(
        `${config.public.apiBase}/api/v1/scraping-jobs/${currentJob.value.id}`,
        { method: 'GET', headers: authHeaders() },
      )
      const wasDone: boolean = currentJob.value.status === 'completed'
      currentJob.value = response
      if (response.status === 'completed' || response.status === 'failed' || response.status === 'cancelled') {
        stopPolling()
        isCancelling.value = false
        await loadRecent()
        if (response.status === 'completed' && !wasDone) {
          completedSignal.value += 1
          void maybeAutoEnrichFacebook(response)
        }
      }
    } catch {
      // Ignore transient refresh errors.
    } finally {
      isRefreshing.value = false
    }
  }

  /**
   * Create and stream a scraping job — shared by user searches and match-loop rounds.
   * @param body - The job creation payload (snake_case, as the API expects).
   * @returns The created job.
   */
  async function launchJob(body: Record<string, unknown>): Promise<ScrapingJob> {
    const response: ScrapingJob = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body,
    })
    currentJob.value = response
    stream.reset()
    attachStream(response)
    startPolling()
    return response
  }

  /**
   * Start a new search.
   * @param params - The search parameters.
   * @returns A promise resolved once the job is created.
   */
  async function startSearch(params: ProspectSearchParams): Promise<void> {
    isStarting.value = true
    try {
      autoEnrich.value = null
      facebookKeptProspects.value = []
      await launchJob({
        category: params.category || null,
        city: params.city || null,
        country: params.country,
        max_results: params.maxResults,
        source: params.source || null,
        skip_duplicates: params.skipDuplicates,
        only_without_website: params.onlyWithoutWebsite,
      })
    } finally {
      isStarting.value = false
    }
  }

  /**
   * Cancel the current running search (e.g. launched by mistake).
   * The scrape stops gracefully; prospects already found are kept.
   * @returns A promise resolved once the cancel request is acknowledged.
   */
  async function cancelSearch(): Promise<void> {
    const job: ScrapingJob | null = currentJob.value
    if (!job || (job.status !== 'running' && job.status !== 'pending')) return
    isCancelling.value = true
    try {
      await $fetch(`${config.public.apiBase}/api/v1/scraping-jobs/${job.id}/cancel`, {
        method: 'POST',
        headers: authHeaders(),
      })
      // The job flips to 'cancelled' via the stream ('cancelled') or the poll.
    } catch {
      isCancelling.value = false
    }
  }

  /**
   * Load a specific job by id and stream it.
   * @param jobId - The job id.
   * @returns A promise resolved once loaded.
   */
  async function loadJob(jobId: string): Promise<void> {
    const response: ScrapingJob = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs/${jobId}`, {
      method: 'GET',
      headers: authHeaders(),
    })
    currentJob.value = response
    stream.reset()
    attachStream(response)
    if (response.status === 'running' || response.status === 'pending') startPolling()
  }

  /**
   * Fetch every job of the user from the API.
   * @returns The raw job list.
   */
  async function fetchJobs(): Promise<ScrapingJob[]> {
    return await $fetch<ScrapingJob[]>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
      method: 'GET',
      headers: authHeaders(),
    })
  }

  /**
   * The prospects a search actually kept — including its automatic Facebook rounds,
   * which are separate jobs linked by ``parent_job_id`` (one user search = one row).
   * @param job - The origin job (a row of the recent-searches list).
   * @returns The kept prospects with fresh data, in creation order.
   */
  async function loadJobProspects(job: ScrapingJob): Promise<Prospect[]> {
    const [prospects, jobs]: [Prospect[], ScrapingJob[]] = await Promise.all([
      ProspectsService.listProspects(),
      fetchJobs(),
    ])
    const family: ScrapingJob[] = [
      job,
      ...jobs.filter((candidate: ScrapingJob): boolean => candidate.parent_job_id === job.id),
    ].sort(
      (a: ScrapingJob, b: ScrapingJob): number => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    )
    const order: Map<number, number> = new Map(
      family
        .flatMap((member: ScrapingJob): number[] => member.results)
        .map((id: number, index: number): [number, number] => [id, index]),
    )
    return prospects
      .filter((prospect: Prospect): boolean => order.has(prospect.id))
      .sort((a: Prospect, b: Prospect): number => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
  }

  /**
   * Load the user's recent jobs (and adopt a running one if idle).
   * @returns A promise resolved once loaded.
   */
  async function loadRecent(): Promise<void> {
    try {
      const response: ScrapingJob[] = await fetchJobs()
      recentJobs.value = [...response]
        // Automatic rounds fold into their origin search — never listed on their own.
        .filter((job: ScrapingJob): boolean => !job.parent_job_id)
        .sort(
          (a: ScrapingJob, b: ScrapingJob): number =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
        .slice(0, 5)
      if (!currentJob.value) {
        const running: ScrapingJob | undefined = recentJobs.value.find(
          (j: ScrapingJob): boolean => j.status === 'running',
        )
        if (running) {
          currentJob.value = running
          stream.reset()
          attachStream(running)
          startPolling()
        }
      }
    } catch {
      // Ignore — recent jobs are non-critical.
    }
  }

  /** Clear the current job and disconnect the stream. */
  function reset(): void {
    currentJob.value = null
    autoEnrich.value = null
    facebookKeptProspects.value = []
    stream.disconnect()
    stream.reset()
    stopPolling()
  }

  return {
    currentJob,
    recentJobs,
    isStarting,
    isCancelling,
    isRefreshing,
    completedSignal,
    autoEnrich,
    facebookKeptProspects,
    displayProgress,
    liveProgress,
    streamLogs,
    streamProspects,
    streamConnected,
    streamSkipped,
    isSearching,
    startSearch,
    cancelSearch,
    refreshJobStatus,
    loadJob,
    loadJobProspects,
    loadRecent,
    reset,
  }
})
