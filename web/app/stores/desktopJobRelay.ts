/**
 * Desktop job relay store — the desktop app does the work other devices leave for it (enrichments, for a start).
 */
import type { UseToastReturn } from '~/types/Composables'
import type { DesktopJob } from '~/services/desktopJobService'
import type { ProspectEnrichment } from '~/services/enrichmentService'
import { defineStore } from 'pinia'
import { useToast } from '~/composables/useToast'
import { ApiClient } from '~/services/api'
import { DesktopJobService } from '~/services/desktopJobService'
import { getScraperSidecarInfo, postToScraperSidecar } from '~/services/scraperSidecarService'
import { useUserStore } from '~/stores/user'

const JOB_LOOKUP_INTERVAL_MS: number = 20_000

const ENRICHMENT_SCRAPE_TIMEOUT_MS: number = 240_000

const ENRICHMENT_FAILED_MESSAGE: string = "L'enrichissement sur votre PC a échoué. Relancez-le."

const LOCAL_SCRAPER_UNAVAILABLE_MESSAGE: string = 'Le Chrome de votre PC ne répond pas. Relancez l’enrichissement.'

const UNKNOWN_KIND_MESSAGE: string = "L'application de ce PC ne sait pas encore faire ce travail : mettez-la à jour."

/** What a batch of jobs gave, for the one summary toast. */
type JobBatchOutcome = {
  done: number
  failed: number
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useDesktopJobRelayStore = defineStore('desktopJobRelay', () => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const toast: UseToastReturn = useToast()

  let lookupTimer: ReturnType<typeof setTimeout> | null = null
  let isWatchingJobs: boolean = false
  let isHandlingJobs: boolean = false

  /**
   * Read a prospect's pages with this computer's Chrome and save them, as the drawer does on the desktop.
   * @param job - The enrichment job, whose payload is the scraper request.
   * @returns The reason the enrichment failed, or null when the record is saved.
   */
  async function enrichProspect(job: DesktopJob): Promise<string | null> {
    if (job.subject_id === null) return ENRICHMENT_FAILED_MESSAGE
    const payload: Record<string, unknown> = job.payload ?? {}
    const scraped: unknown = await postToScraperSidecar<unknown>(
      '/scraper/enrichment',
      {
        business_name: payload.business_name,
        city: payload.city ?? null,
        google_maps_url: payload.google_maps_url ?? null,
        facebook_url: payload.facebook_url ?? null,
        country: payload.country ?? 'FR',
      },
      { timeoutMs: ENRICHMENT_SCRAPE_TIMEOUT_MS },
    )
    if (scraped === null) return LOCAL_SCRAPER_UNAVAILABLE_MESSAGE
    const record: ProspectEnrichment = await ApiClient.post<ProspectEnrichment>(
      `/api/v1/prospects/${job.subject_id}/enrichment/run`,
      scraped,
    )
    if (record.status === 'completed') return null
    return record.error_message || ENRICHMENT_FAILED_MESSAGE
  }

  /**
   * Put a local failure into words the other device understands (a network error means Chrome is not answering).
   * @param err - What the local tools threw.
   * @returns The reason shown on the record.
   */
  function describeFailure(err: unknown): string {
    if (err instanceof TypeError) return LOCAL_SCRAPER_UNAVAILABLE_MESSAGE
    return err instanceof Error && err.message ? err.message : ENRICHMENT_FAILED_MESSAGE
  }

  /**
   * Do one job on this computer, then close it as done or failed.
   * @param job - The job another device asked for.
   * @returns True when the work is saved, false when it failed or was taken by another computer.
   */
  async function handleJob(job: DesktopJob): Promise<boolean> {
    try {
      await DesktopJobService.claim(job.id)
    } catch {
      return false
    }
    let failureMessage: string | null
    try {
      failureMessage = job.kind === 'prospect_enrichment' ? await enrichProspect(job) : UNKNOWN_KIND_MESSAGE
    } catch (err: unknown) {
      failureMessage = describeFailure(err)
    }
    if (failureMessage === null) {
      await DesktopJobService.complete(job.id).catch((): void => {})
      return true
    }
    await DesktopJobService.fail(job.id, failureMessage).catch((): void => {})
    return false
  }

  /**
   * Tell the person at the computer how a batch ended.
   * @param outcome - How many jobs are saved and how many failed.
   */
  function announceBatchOutcome(outcome: JobBatchOutcome): void {
    const total: number = outcome.done + outcome.failed
    if (total === 0) return
    const summary: string =
      total > 1 ? `${total} travaux demandés depuis un autre appareil` : 'Travail demandé depuis un autre appareil'
    if (outcome.failed === 0) {
      toast.success(`${summary} : terminé sur ce PC.`)
      return
    }
    toast.error(`${summary} : ${outcome.failed} en échec, voir la fiche concernée.`)
  }

  /**
   * Do every job waiting for this computer, oldest first. Does nothing outside the desktop app.
   * @returns A promise resolved once no job is left, or the watch was stopped.
   */
  async function handleWaitingJobs(): Promise<void> {
    if (isHandlingJobs || !userStore.token) return
    isHandlingJobs = true
    try {
      const hasLocalTools: boolean = (await getScraperSidecarInfo()) !== null
      if (!hasLocalTools) return
      const jobs: DesktopJob[] = await DesktopJobService.listWaiting().catch((): DesktopJob[] => [])
      if (jobs.length === 0) return
      toast.info(
        jobs.length > 1
          ? `${jobs.length} travaux demandés depuis un autre appareil : ce PC s'en occupe.`
          : 'Travail demandé depuis un autre appareil : ce PC s’en occupe.',
      )
      const outcome: JobBatchOutcome = { done: 0, failed: 0 }
      for (const job of jobs) {
        if (!isWatchingJobs) break
        if (await handleJob(job)) outcome.done += 1
        else outcome.failed += 1
      }
      announceBatchOutcome(outcome)
    } finally {
      isHandlingJobs = false
    }
  }

  /**
   * Plan the next look for waiting jobs, while the shell watches.
   * @param delayMs - Delay before the look.
   */
  function scheduleLookup(delayMs: number): void {
    if (lookupTimer !== null) clearTimeout(lookupTimer)
    lookupTimer = setTimeout(async (): Promise<void> => {
      lookupTimer = null
      await handleWaitingJobs()
      if (isWatchingJobs && lookupTimer === null) scheduleLookup(JOB_LOOKUP_INTERVAL_MS)
    }, delayMs)
  }

  /** Start looking for the work other devices leave for this computer (called once by the dashboard shell). */
  function startWatching(): void {
    if (!import.meta.client || isWatchingJobs) return
    isWatchingJobs = true
    scheduleLookup(0)
  }

  /** Stop looking (the dashboard shell is gone); a job under way still ends and is closed. */
  function stopWatching(): void {
    isWatchingJobs = false
    if (lookupTimer !== null) {
      clearTimeout(lookupTimer)
      lookupTimer = null
    }
  }

  return { startWatching, stopWatching }
})
