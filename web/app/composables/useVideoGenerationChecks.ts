import type { Ref } from 'vue'
import type { UseVideoGenerationChecksReturn, VideoGenerationCheckPace } from '~/types/Composables'
import { onScopeDispose, ref } from 'vue'

const VIDEO_GENERATION_CHECK_PACE: VideoGenerationCheckPace[] = [
  { untilMinutes: 2, everySeconds: 5 },
  { untilMinutes: 5, everySeconds: 15 },
  { untilMinutes: 15, everySeconds: 30 },
]

/**
 * Follow a video generation running on the server: check less and less often, and stop after fifteen minutes.
 * @param refreshVideoStatus - Reloads what shows the video, its generation status included.
 * @param isVideoGenerating - Whether the video is still pending or generating.
 * @returns The check controls, and whether the video outlasted the checks.
 */
export function useVideoGenerationChecks(
  refreshVideoStatus: () => Promise<void>,
  isVideoGenerating: () => boolean,
): UseVideoGenerationChecksReturn {
  const isTakingLongerThanExpected: Ref<boolean> = ref(false)
  let nextCheckTimer: ReturnType<typeof setTimeout> | null = null
  let checksStartedAt: number = 0
  let isFollowing: boolean = false
  let isScopeDisposed: boolean = false

  /** Follow the generation from now on, from the fastest pace. */
  function startChecks(): void {
    if (isScopeDisposed) return
    stopChecks()
    isFollowing = true
    isTakingLongerThanExpected.value = false
    checksStartedAt = Date.now()
    scheduleNextCheck()
  }

  /** Stop checking the video status. */
  function stopChecks(): void {
    isFollowing = false
    if (nextCheckTimer !== null) {
      clearTimeout(nextCheckTimer)
      nextCheckTimer = null
    }
  }

  /** Plan the next check at the pace of the time spent, or give up once the last pace is over. */
  function scheduleNextCheck(): void {
    if (!isFollowing || nextCheckTimer !== null) return
    const elapsedMinutes: number = (Date.now() - checksStartedAt) / 60000
    const pace: VideoGenerationCheckPace | undefined = VIDEO_GENERATION_CHECK_PACE.find(
      (candidate: VideoGenerationCheckPace): boolean => elapsedMinutes < candidate.untilMinutes,
    )
    if (!pace) {
      isTakingLongerThanExpected.value = isVideoGenerating()
      return
    }
    nextCheckTimer = setTimeout(checkVideoStatus, pace.everySeconds * 1000)
  }

  /**
   * Reload the video status, then plan the next check while the video is still generating.
   * @returns A promise resolved once checked.
   */
  async function checkVideoStatus(): Promise<void> {
    nextCheckTimer = null
    try {
      await refreshVideoStatus()
    } catch {
      // A missed check is not worth a toast.
    }
    if (isFollowing && isVideoGenerating()) scheduleNextCheck()
  }

  /**
   * Reload the video status once, on demand, after the checks gave up.
   * @returns A promise resolved once reloaded.
   * @throws When the reload fails.
   */
  async function checkNow(): Promise<void> {
    await refreshVideoStatus()
    if (!isVideoGenerating()) isTakingLongerThanExpected.value = false
  }

  onScopeDispose((): void => {
    isScopeDisposed = true
    stopChecks()
  })

  return { isTakingLongerThanExpected, startChecks, stopChecks, checkNow }
}
