/**
 * Desktop video relay store — the desktop app builds the prospection videos asked from a tablet or a phone.
 */
import type { UseToastReturn } from '~/types/Composables'
import type { DemoSiteDesktopVideoRequest } from '~/services/demoSiteService'
import type { FullVideoBuildResult } from '~/services/storyblokSidecarService'
import { defineStore } from 'pinia'
import { useToast } from '~/composables/useToast'
import { DemoSiteService } from '~/services/demoSiteService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { useUserStore } from '~/stores/user'

const REQUEST_LOOKUP_INTERVAL_MS: number = 20_000

const STORYBLOK_DISCONNECTED_MESSAGE: string =
  "Storyblok est déconnecté sur votre PC. Reconnectez-le dans l'application Windows (Paramètres, Vidéo de prospection, « Connexion Storyblok »), puis redemandez la vidéo."

const LOCAL_BUILD_FAILED_MESSAGE: string = 'La génération sur votre PC a échoué. Redemandez la vidéo.'

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
  function describeBuildFailure(build: FullVideoBuildResult): string {
    if (build.status === 'needs_login') return STORYBLOK_DISCONNECTED_MESSAGE
    return build.message ?? LOCAL_BUILD_FAILED_MESSAGE
  }

  /**
   * Build one requested video on this computer and publish it, or report why it could not be built.
   * @param request - The site whose video another device asked for.
   * @returns A promise resolved once the video is published or its failure is reported.
   */
  async function buildRequestedVideo(request: DemoSiteDesktopVideoRequest): Promise<void> {
    try {
      await DemoSiteService.claimDesktopVideo(request.demo_site_id)
    } catch {
      return
    }
    toast.info(`Vidéo de « ${request.business_name} » demandée depuis un autre appareil : ce PC la génère.`)
    let build: FullVideoBuildResult
    try {
      build = await StoryblokSidecarService.buildFullVideo(request.demo_site_id)
    } catch (err: unknown) {
      build = { status: 'failed', message: err instanceof Error && err.message ? err.message : undefined }
    }
    if (build.status === 'done') {
      toast.success(`Vidéo de « ${request.business_name} » générée et publiée.`)
      return
    }
    const failureMessage: string = describeBuildFailure(build)
    toast.error(`Vidéo de « ${request.business_name} » : ${failureMessage}`)
    await DemoSiteService.reportDesktopVideoFailure(request.demo_site_id, failureMessage).catch((): void => {})
  }

  /**
   * Build every video waiting for this computer, oldest request first. Does nothing outside the desktop app.
   * @returns A promise resolved once no request is left, or the watch was stopped.
   */
  async function handleWaitingRequests(): Promise<void> {
    if (isHandlingRequests || !userStore.token) return
    isHandlingRequests = true
    try {
      const hasLocalVideoBuilder: boolean = (await getScraperSidecarInfo()) !== null
      if (!hasLocalVideoBuilder) return
      const requests: DemoSiteDesktopVideoRequest[] = await DemoSiteService.listDesktopVideoRequests().catch(
        (): DemoSiteDesktopVideoRequest[] => [],
      )
      for (const request of requests) {
        if (!isWatchingRequests) return
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
