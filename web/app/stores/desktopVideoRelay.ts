/**
 * Desktop video relay store — the desktop app builds the prospection videos of demo sites and receptionists
 * asked from a tablet, a phone or the automatic generation.
 */
import type { AiAssistantDesktopVideoRequest } from '~/types/AiAssistant'
import type { UseToastReturn } from '~/types/Composables'
import type {
  DesktopVideoBuildOutcome,
  DesktopVideoRequest,
  DesktopVideoSubjectKind,
  DesktopVideoSubjectRelay,
} from '~/types/DesktopVideoRelay'
import type { DemoSiteDesktopVideoRequest } from '~/services/demoSiteService'
import { defineStore } from 'pinia'
import { useToast } from '~/composables/useToast'
import { AiAssistantService } from '~/services/aiAssistantService'
import { AssistantSidecarService } from '~/services/assistantSidecarService'
import { DemoSiteService } from '~/services/demoSiteService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { useUserStore } from '~/stores/user'
import { parseApiDate } from '~/utils/date'

const REQUEST_LOOKUP_INTERVAL_MS: number = 20_000

const STORYBLOK_DISCONNECTED_MESSAGE: string =
  "Storyblok est déconnecté sur votre PC. Reconnectez-le dans l'application Windows (Paramètres, Vidéo de prospection, « Connexion Storyblok »), puis redemandez la vidéo."

const LOCAL_BUILD_FAILED_MESSAGE: string = 'La génération sur votre PC a échoué. Redemandez la vidéo.'

const SUBJECT_RELAYS: Record<DesktopVideoSubjectKind, DesktopVideoSubjectRelay> = {
  site: {
    describeVideo: (businessName: string): string => `Vidéo de « ${businessName} »`,
    claim: async (subjectId: number): Promise<void> => {
      await DemoSiteService.claimDesktopVideo(subjectId)
    },
    build: (subjectId: number): Promise<DesktopVideoBuildOutcome> => StoryblokSidecarService.buildFullVideo(subjectId),
    reportFailure: async (subjectId: number, message: string): Promise<void> => {
      await DemoSiteService.reportDesktopVideoFailure(subjectId, message)
    },
  },
  assistant: {
    describeVideo: (businessName: string): string => `Vidéo de la réceptionniste de « ${businessName} »`,
    claim: async (subjectId: number): Promise<void> => {
      await AiAssistantService.claimDesktopVideo(subjectId)
    },
    build: (subjectId: number): Promise<DesktopVideoBuildOutcome> => AssistantSidecarService.buildFullVideo(subjectId),
    reportFailure: async (subjectId: number, message: string): Promise<void> => {
      await AiAssistantService.reportDesktopVideoFailure(subjectId, message)
    },
  },
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useDesktopVideoRelayStore = defineStore('desktopVideoRelay', () => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const toast: UseToastReturn = useToast()

  let lookupTimer: ReturnType<typeof setTimeout> | null = null
  let isWatchingRequests: boolean = false
  let isHandlingRequests: boolean = false

  /**
   * Put into words why a requested video could not be built, for the device that asked for it.
   * @param build - The outcome of the local build.
   * @returns The reason, with what to do next.
   */
  function describeBuildFailure(build: DesktopVideoBuildOutcome): string {
    if (build.status === 'needs_login') {
      return STORYBLOK_DISCONNECTED_MESSAGE
    }
    return build.message ?? LOCAL_BUILD_FAILED_MESSAGE
  }

  /**
   * Gather the site and receptionist videos waiting for this computer, oldest request first.
   * @returns The waiting requests; a list that cannot be read counts as empty until the next look.
   */
  async function listWaitingRequests(): Promise<DesktopVideoRequest[]> {
    const [siteRequests, assistantRequests]: [DemoSiteDesktopVideoRequest[], AiAssistantDesktopVideoRequest[]] =
      await Promise.all([
        DemoSiteService.listDesktopVideoRequests().catch((): DemoSiteDesktopVideoRequest[] => []),
        AiAssistantService.listDesktopVideoRequests().catch((): AiAssistantDesktopVideoRequest[] => []),
      ])
    const requests: DesktopVideoRequest[] = [
      ...siteRequests.map(
        (request: DemoSiteDesktopVideoRequest): DesktopVideoRequest => ({
          kind: 'site',
          subjectId: request.demo_site_id,
          businessName: request.business_name,
          requestedAt: request.requested_at,
        }),
      ),
      ...assistantRequests.map(
        (request: AiAssistantDesktopVideoRequest): DesktopVideoRequest => ({
          kind: 'assistant',
          subjectId: request.assistant_id,
          businessName: request.business_name,
          requestedAt: request.requested_at,
        }),
      ),
    ]
    return requests.sort(
      (first: DesktopVideoRequest, second: DesktopVideoRequest): number =>
        parseApiDate(first.requestedAt).getTime() - parseApiDate(second.requestedAt).getTime(),
    )
  }

  /**
   * Build one requested video on this computer and publish it, or report why it could not be built.
   * @param request - The site or receptionist whose video another device asked for.
   * @returns A promise resolved once the video is published or its failure is reported.
   */
  async function buildRequestedVideo(request: DesktopVideoRequest): Promise<void> {
    const subjectRelay: DesktopVideoSubjectRelay = SUBJECT_RELAYS[request.kind]
    const videoName: string = subjectRelay.describeVideo(request.businessName)
    try {
      await subjectRelay.claim(request.subjectId)
    } catch {
      return
    }
    toast.info(`${videoName} demandée depuis un autre appareil : ce PC la génère.`)
    let build: DesktopVideoBuildOutcome
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
      const requests: DesktopVideoRequest[] = await listWaitingRequests()
      for (const request of requests) {
        if (!isWatchingRequests) {
          return
        }
        await buildRequestedVideo(request)
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
