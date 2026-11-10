/**
 * Desktop video relay store — the desktop app builds every prospection video left waiting for it: the demo sites',
 * and those of the kinds of demo the product modules register in the `DesktopVideoSubjectRegistry`.
 */
import type { UseToastReturn } from '~/types/Composables'
import type { DesktopVideoRequest, DesktopVideoSubjectRelay } from '~/types/DesktopVideoRelay'
import type { DemoSiteDesktopVideoRequest } from '~/services/demoSiteService'
import type { FullVideoBuildResult } from '~/services/storyblokSidecarService'
import { defineStore } from 'pinia'
import { useToast } from '~/composables/useToast'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { DemoSiteService } from '~/services/demoSiteService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { useModuleStore } from '~/stores/moduleStore'
import { useUserStore } from '~/stores/user'
import { parseApiDate } from '~/utils/date'
import { DesktopVideoSubjectRegistry } from '~/utils/desktopVideoSubjectRegistry'

const REQUEST_LOOKUP_INTERVAL_MS: number = 20_000

const STORYBLOK_DISCONNECTED_MESSAGE: string =
  "Storyblok est déconnecté sur votre PC. Reconnectez-le dans l'application Windows (Paramètres, Vidéo de prospection, « Connexion Storyblok »), puis redemandez la vidéo."

const LOCAL_BUILD_FAILED_MESSAGE: string = 'La génération sur votre PC a échoué. Redemandez la vidéo.'

/** The demo sites' videos, the core's own kind of desktop video. */
const SITE_SUBJECT_RELAY: DesktopVideoSubjectRelay = {
  kind: 'site',
  moduleKey: WEBSITES_MODULE_KEY,
  listWaitingRequests: async (): Promise<DesktopVideoRequest[]> => {
    const siteRequests: DemoSiteDesktopVideoRequest[] = await DemoSiteService.listDesktopVideoRequests()
    return siteRequests.map(
      (request: DemoSiteDesktopVideoRequest): DesktopVideoRequest => ({
        kind: 'site',
        subjectId: request.demo_site_id,
        businessName: request.business_name,
        requestedAt: request.requested_at,
      }),
    )
  },
  describeVideo: (businessName: string): string => `Vidéo de « ${businessName} »`,
  claim: async (subjectId: number): Promise<void> => {
    await DemoSiteService.claimDesktopVideo(subjectId)
  },
  build: (subjectId: number): Promise<FullVideoBuildResult> => StoryblokSidecarService.buildFullVideo(subjectId),
  reportFailure: async (subjectId: number, message: string): Promise<void> => {
    await DemoSiteService.reportDesktopVideoFailure(subjectId, message)
  },
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useDesktopVideoRelayStore = defineStore('desktopVideoRelay', () => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()
  const toast: UseToastReturn = useToast()

  let lookupTimer: ReturnType<typeof setTimeout> | null = null
  let isWatchingRequests: boolean = false
  let isHandlingRequests: boolean = false

  /**
   * Put into words why a requested video could not be built, for the device that asked for it.
   * @param build - The outcome of the local build.
   * @returns The reason, with what to do next.
   */
  function describeBuildFailure(build: FullVideoBuildResult): string {
    if (build.status === 'needs_login') {
      return STORYBLOK_DISCONNECTED_MESSAGE
    }
    return build.message ?? LOCAL_BUILD_FAILED_MESSAGE
  }

  /**
   * The kinds of video this computer builds: the demo sites', then those of the modules switched on.
   * @returns The relays to look at.
   */
  async function listSubjectRelays(): Promise<DesktopVideoSubjectRelay[]> {
    await moduleStore.ensureEnabledModulesLoaded()
    return [
      SITE_SUBJECT_RELAY,
      ...DesktopVideoSubjectRegistry.list().filter((relay: DesktopVideoSubjectRelay): boolean =>
        moduleStore.isModuleUsable(relay.moduleKey),
      ),
    ]
  }

  /**
   * Gather every video waiting for this computer, oldest request first.
   * @param relays - The kinds of video to look at.
   * @returns The waiting requests; a list that cannot be read counts as empty until the next look.
   */
  async function listWaitingRequests(relays: DesktopVideoSubjectRelay[]): Promise<DesktopVideoRequest[]> {
    const requestsByKind: DesktopVideoRequest[][] = await Promise.all(
      relays.map(
        (relay: DesktopVideoSubjectRelay): Promise<DesktopVideoRequest[]> =>
          relay.listWaitingRequests().catch((): DesktopVideoRequest[] => []),
      ),
    )
    const requests: DesktopVideoRequest[] = requestsByKind.flat()
    return requests.sort(
      (first: DesktopVideoRequest, second: DesktopVideoRequest): number =>
        parseApiDate(first.requestedAt).getTime() - parseApiDate(second.requestedAt).getTime(),
    )
  }

  /**
   * Build one requested video on this computer and publish it, or report why it could not be built.
   * @param request - The demo whose video another device asked for.
   * @param subjectRelay - How to claim, build and report a video of its kind.
   * @returns A promise resolved once the video is published or its failure is reported.
   */
  async function buildRequestedVideo(
    request: DesktopVideoRequest,
    subjectRelay: DesktopVideoSubjectRelay,
  ): Promise<void> {
    const videoName: string = subjectRelay.describeVideo(request.businessName)
    try {
      await subjectRelay.claim(request.subjectId)
    } catch {
      return
    }
    toast.info(`${videoName} : ce PC la génère.`)
    let build: FullVideoBuildResult
    try {
      build = await subjectRelay.build(request.subjectId)
    } catch (err: unknown) {
      build = { status: 'failed', message: err instanceof Error && err.message ? err.message : undefined }
    }
    if (build.status === 'done') {
      toast.success(`${videoName} générée et publiée.`)
      return
    }
    const failureMessage: string = describeBuildFailure(build)
    toast.error(`${videoName} : ${failureMessage}`)
    await subjectRelay.reportFailure(request.subjectId, failureMessage).catch((): void => {})
  }

  /**
   * Build every video waiting for this computer, oldest request first. Does nothing outside the desktop app.
   * @returns A promise resolved once no request is left, or the watch was stopped.
   */
  async function handleWaitingRequests(): Promise<void> {
    if (isHandlingRequests || !userStore.token) {
      return
    }
    isHandlingRequests = true
    try {
      const hasLocalVideoBuilder: boolean = (await getScraperSidecarInfo()) !== null
      if (!hasLocalVideoBuilder) {
        return
      }
      const relays: DesktopVideoSubjectRelay[] = await listSubjectRelays()
      const requests: DesktopVideoRequest[] = await listWaitingRequests(relays)
      for (const request of requests) {
        if (!isWatchingRequests) {
          return
        }
        const subjectRelay: DesktopVideoSubjectRelay | undefined = relays.find(
          (relay: DesktopVideoSubjectRelay): boolean => relay.kind === request.kind,
        )

        if (subjectRelay) {
          await buildRequestedVideo(request, subjectRelay)
        }
      }
    } finally {
      isHandlingRequests = false
    }
  }

  /**
   * Plan the next look for waiting requests, while the shell watches.
   * @param delayMs - Delay before the look.
   */
  function scheduleLookup(delayMs: number): void {
    if (lookupTimer !== null) clearTimeout(lookupTimer)
    lookupTimer = setTimeout(async (): Promise<void> => {
      lookupTimer = null
      await handleWaitingRequests()
      if (isWatchingRequests && lookupTimer === null) scheduleLookup(REQUEST_LOOKUP_INTERVAL_MS)
    }, delayMs)
  }

  /** Start looking for the videos other devices ask this computer to build (called once by the dashboard shell). */
  function startWatching(): void {
    if (!import.meta.client || isWatchingRequests) return
    isWatchingRequests = true
    scheduleLookup(0)
  }

  /** Stop looking (the dashboard shell is gone); a build under way still ends and publishes its video. */
  function stopWatching(): void {
    isWatchingRequests = false
    if (lookupTimer !== null) {
      clearTimeout(lookupTimer)
      lookupTimer = null
    }
  }

  return { startWatching, stopWatching }
})
