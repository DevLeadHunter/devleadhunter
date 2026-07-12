/**
 * Shared prospect-search store — owns a scraping job's lifecycle so the search
 * form (a drawer) and the results (the search page or the automatisation tunnel)
 * all read the same state.
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useRuntimeConfig } from '#app'
import { useUserStore } from '~/stores/user'
import { useScrapingJobStream } from '~/composables/useScrapingJobStream'
import type { ScrapingJobProgressState } from '~/composables/useScrapingJobStream'
import type { Prospect } from '~/types'

/** A scraping job as returned by the API. */
export interface ScrapingJob {
  id: string
  user_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  category: string | null
  city: string | null
  max_results: number
  source: string | null
  skip_duplicates: boolean
  progress: ScrapingJobProgressState
  logs?: string[]
  live_prospects?: Prospect[]
  results: number[]
  skipped_duplicates: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

/** Parameters for starting a search. */
export interface ProspectSearchParams {
  category: string
  city: string
  maxResults: number
  source: string
  skipDuplicates: boolean
  onlyWithoutWebsite: boolean
}

export const useProspectSearchStore = defineStore('prospectSearch', () => {
  const config = useRuntimeConfig()
  const userStore = useUserStore()
  const stream = useScrapingJobStream()

  /** The job currently displayed (running or last finished). */
  const currentJob: Ref<ScrapingJob | null> = ref<ScrapingJob | null>(null)
  /** The user's recent jobs. */
  const recentJobs: Ref<ScrapingJob[]> = ref<ScrapingJob[]>([])
  /** Whether a job is being started. */
  const isStarting: Ref<boolean> = ref<boolean>(false)
  /** Whether a manual refresh is in flight. */
  const isRefreshing: Ref<boolean> = ref<boolean>(false)
  /** Bumped each time a job completes — watch it to react (e.g. refresh a list). */
  const completedSignal: Ref<number> = ref<number>(0)

  let pollInterval: ReturnType<typeof setInterval> | null = null

  /** Live progress (stream first, then the job snapshot). */
  const liveProgress: ComputedRef<ScrapingJobProgressState> = computed((): ScrapingJobProgressState => {
    if (stream.progress.value.total > 0 || stream.progress.value.current > 0) return stream.progress.value
    return currentJob.value?.progress ?? stream.progress.value
  })
  const streamLogs: ComputedRef<string[]> = computed((): string[] => stream.logs.value)
  const streamProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => stream.prospects.value)
  const streamConnected: ComputedRef<boolean> = computed((): boolean => stream.isConnected.value)
  const streamSkipped: ComputedRef<number> = computed((): number => stream.skippedDuplicates.value)

  /** Whether a search is currently running. */
  const isSearching: ComputedRef<boolean> = computed(
    (): boolean => currentJob.value?.status === 'running' || currentJob.value?.status === 'pending',
  )

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
      },
      onError: async (): Promise<void> => {
        stopPolling()
        await refreshJobStatus()
      },
    })
  }

  /**
   * Refresh the current job's status from the API.
   * @returns A promise resolved once refreshed.
   */
  async function refreshJobStatus(): Promise<void> {
    if (!currentJob.value) return
    try {
      isRefreshing.value = true
      const response = await $fetch<ScrapingJob>(
        `${config.public.apiBase}/api/v1/scraping-jobs/${currentJob.value.id}`,
        { method: 'GET', headers: authHeaders() },
      )
      const wasDone: boolean = currentJob.value.status === 'completed'
      currentJob.value = response
      if (response.status === 'completed' || response.status === 'failed') {
        stopPolling()
        await loadRecent()
        if (response.status === 'completed' && !wasDone) completedSignal.value += 1
      }
    } catch {
      // Ignore transient refresh errors.
    } finally {
      isRefreshing.value = false
    }
  }

  /**
   * Start a new search.
   * @param params - The search parameters.
   * @returns A promise resolved once the job is created.
   */
  async function startSearch(params: ProspectSearchParams): Promise<void> {
    isStarting.value = true
    try {
      const response = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: {
          category: params.category || null,
          city: params.city || null,
          max_results: params.maxResults,
          source: params.source || null,
          skip_duplicates: params.skipDuplicates,
          only_without_website: params.onlyWithoutWebsite,
        },
      })
      currentJob.value = response
      stream.reset()
      attachStream(response)
      startPolling()
    } finally {
      isStarting.value = false
    }
  }

  /**
   * Load a specific job by id and stream it.
   * @param jobId - The job id.
   * @returns A promise resolved once loaded.
   */
  async function loadJob(jobId: string): Promise<void> {
    const response = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs/${jobId}`, {
      method: 'GET',
      headers: authHeaders(),
    })
    currentJob.value = response
    stream.reset()
    attachStream(response)
    if (response.status === 'running' || response.status === 'pending') startPolling()
  }

  /**
   * Load the user's recent jobs (and adopt a running one if idle).
   * @returns A promise resolved once loaded.
   */
  async function loadRecent(): Promise<void> {
    try {
      const response = await $fetch<ScrapingJob[]>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
        method: 'GET',
        headers: authHeaders(),
      })
      recentJobs.value = [...response]
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
    stream.disconnect()
    stream.reset()
    stopPolling()
  }

  return {
    currentJob,
    recentJobs,
    isStarting,
    isRefreshing,
    completedSignal,
    liveProgress,
    streamLogs,
    streamProspects,
    streamConnected,
    streamSkipped,
    isSearching,
    startSearch,
    refreshJobStatus,
    loadJob,
    loadRecent,
    reset,
  }
})
