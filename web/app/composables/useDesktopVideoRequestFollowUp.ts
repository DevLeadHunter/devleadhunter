import type { UseDesktopVideoRequestFollowUpReturn, UseToastReturn } from '~/types/Composables'
import type { ProspectionVideoSubject } from '~/types/ProspectionVideo'
import { onScopeDispose } from 'vue'
import { useToast } from '~/composables/useToast'

const WAITING_CHECK_INTERVAL_MS: number = 15_000

const BUILDING_CHECK_INTERVAL_MS: number = 5_000

/**
 * Follow a video asked from the owner's PC until it is published or given up, then tell how it ended.
 * @param readVideoState - Reloads the video's state into the followed demo site or receptionist.
 * @param followedSubject - The demo site or receptionist whose video is followed, as last read.
 * @returns The follow-up controls.
 */
export function useDesktopVideoRequestFollowUp(
  readVideoState: () => Promise<void>,
  followedSubject: () => ProspectionVideoSubject | null,
): UseDesktopVideoRequestFollowUpReturn {
  const toast: UseToastReturn = useToast()
  let nextCheckTimer: ReturnType<typeof setTimeout> | null = null
  let isScopeDisposed: boolean = false

  /**
   * Whether the followed video still waits for the PC or is being built.
   * @returns True while a request is left for the PC.
   */
  function isWaitingForDesktop(): boolean {
    return Boolean(followedSubject()?.video_desktop_requested_at)
  }

  /** Plan the next look at the video: every 15 s while it waits, every 5 s once the PC builds it. */
  function startFollowUp(): void {
    if (isScopeDisposed || nextCheckTimer !== null) {
      return
    }
    const isBuildStarted: boolean = followedSubject()?.is_video_desktop_build_started ?? false
    const delayMs: number = isBuildStarted ? BUILDING_CHECK_INTERVAL_MS : WAITING_CHECK_INTERVAL_MS
    nextCheckTimer = setTimeout(checkVideoState, delayMs)
  }

  /** Stop following the video. */
  function stopFollowUp(): void {
    if (nextCheckTimer !== null) {
      clearTimeout(nextCheckTimer)
      nextCheckTimer = null
    }
  }

  /**
   * Read the video's state once, then plan the next look while it still waits, or tell how the request ended.
   * @returns A promise resolved once the state is read.
   */
  async function checkVideoState(): Promise<void> {
    nextCheckTimer = null
    const wasWaitingForDesktop: boolean = isWaitingForDesktop()
    await readVideoState().catch((): void => {})
    if (isWaitingForDesktop()) {
      startFollowUp()
      return
    }
    if (wasWaitingForDesktop) {
      announceOutcome()
    }
  }

  /** Tell how the followed request ended: the video published, or why the PC gave it up. */
  function announceOutcome(): void {
    const subject: ProspectionVideoSubject | null = followedSubject()
    if (subject?.video_error) {
      toast.error(subject.video_error)
      return
    }
    if (subject?.video_status === 'ready') {
      toast.success('Vidéo générée par votre PC')
    }
  }

  onScopeDispose((): void => {
    isScopeDisposed = true
    stopFollowUp()
  })

  return { startFollowUp, stopFollowUp }
}
