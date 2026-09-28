import type { Ref } from 'vue'
import type { UseVideoGenerationFollowUpReturn, VideoGenerationCheckPace } from '~/types/Composables'
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
 * @returns The follow-up controls, and whether the video outlasted the follow-up.
 */
export function useVideoGenerationFollowUp(
  refreshVideoStatus: () => Promise<void>,
  isVideoGenerating: () => boolean,
): UseVideoGenerationFollowUpReturn {
  const isTakingLongerThanExpected: Ref<boolean> = ref(false)
  let nextCheckTimer: ReturnType<typeof setTimeout> | null = null
  let followUpStartedAt: number = 0

  /** Follow the generation from now on, from the fastest pace. */
  function start(): void {
    stop()
    isTakingLongerThanExpected.value = false
    followUpStartedAt = Date.now()
    scheduleNextCheck()
  }

  /** Stop checking (the page leaves, or the generation is over). */
  function stop(): void {
    if (nextCheckTimer !== null) {
      clearTimeout(nextCheckTimer)
      nextCheckTimer = null
    }
  }

  /** Plan the next check at the pace of the time spent, or give up once the last pace is over. */
  function scheduleNextCheck(): void {
    const elapsedMinutes: number = (Date.now() - followUpStartedAt) / 60000
    const pace: VideoGenerationCheckPace | undefined = VIDEO_GENERATION_CHECK_PACE.find(
      (candidate: VideoGenerationCheckPace): boolean => elapsedMinutes < candidate.untilMinutes,
    )
    if (!pace) {
      nextCheckTimer = null
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
    await refreshVideoStatus()
    if (isVideoGenerating()) scheduleNextCheck()
  }

  /**
   * Reload the video status once, on demand, after the follow-up gave up.
   * @returns A promise resolved once reloaded.
   */
  async function refreshNow(): Promise<void> {
    await refreshVideoStatus()
    if (!isVideoGenerating()) isTakingLongerThanExpected.value = false
  }

  onScopeDispose(stop)

  return { isTakingLongerThanExpected, start, stop, refreshNow }
}
