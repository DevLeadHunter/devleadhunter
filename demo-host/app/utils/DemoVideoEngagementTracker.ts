import type { DemoVideoEventCapture } from '~/types/demoVideoTracking'

const PROGRESS_THRESHOLDS: number[] = [25, 50, 75]
const COMPLETE_THRESHOLD_PERCENT: number = 95
const MAX_COUNTED_TICK_SECONDS: number = 1.5

/**
 * Attaches engagement tracking to the prospection-video player.
 *
 * Watch time is accumulated from wall-clock deltas between `timeupdate` ticks rather than read
 * from `currentTime`, so pauses and seeks never inflate the number the API scores attention on.
 */
export class DemoVideoEngagementTracker {
  private hasFiredPlay: boolean = false
  private hasFiredComplete: boolean = false
  private replayCount: number = 0
  private hasEnded: boolean = false
  private isMuted: boolean
  private seekFromPercent: number = 0
  private readonly reachedThresholds: Set<number> = new Set()

  private watchedSeconds: number = 0
  private lastTickMs: number = 0
  private flushedSeconds: number = 0

  /**
   * @param player - The mounted video element.
   * @param capture - PostHog capture helper from `useDemoVideoTracking`.
   */
  constructor(
    private readonly player: HTMLVideoElement,
    private readonly capture: DemoVideoEventCapture,
  ) {
    this.isMuted = player.muted
  }

  /** Subscribe to every player and document event the tracking relies on. */
  start(): void {
    this.player.addEventListener('play', (): void => this.handlePlay())
    this.player.addEventListener('pause', (): void => this.handlePause())
    this.player.addEventListener('ended', (): void => this.handleEnded())
    this.player.addEventListener('timeupdate', (): void => this.handleTimeUpdate())
    this.player.addEventListener('seeking', (): void => this.handleSeeking())
    this.player.addEventListener('seeked', (): void => this.handleSeeked())
    this.player.addEventListener('volumechange', (): void => this.handleVolumeChange())

    this.player.addEventListener('webkitbeginfullscreen', (): void =>
      this.capture('demo_video_fullscreen', { entered: true }),
    )
    this.player.addEventListener('webkitendfullscreen', (): void =>
      this.capture('demo_video_fullscreen', { entered: false }),
    )
    document.addEventListener('fullscreenchange', (): void => this.handleFullscreenChange())
    document.addEventListener('webkitfullscreenchange', (): void => this.handleFullscreenChange())

    document.addEventListener('visibilitychange', (): void => {
      if (document.visibilityState === 'hidden') {
        this.flushWatchTime()
      }
    })
    window.addEventListener('pagehide', (): void => this.flushWatchTime())
  }

  /**
   * Read the current playback position.
   *
   * @returns The position as an integer percent, or 0 while the duration is unknown.
   */
  private currentPercent(): number {
    if (!this.player.duration || Number.isNaN(this.player.duration)) {
      return 0
    }
    return Math.round((this.player.currentTime / this.player.duration) * 100)
  }

  /** Emit the real watched seconds, skipping the event when nothing was watched since the last flush. */
  private flushWatchTime(): void {
    const seconds: number = Math.round(this.watchedSeconds)
    if (seconds <= this.flushedSeconds) {
      return
    }
    this.flushedSeconds = seconds
    this.capture('demo_video_watch_time', { seconds, percent: this.currentPercent() })
  }

  /** Split a play press into first play, replay from the start, or resume after a pause. */
  private handlePlay(): void {
    if (!this.hasFiredPlay) {
      this.hasFiredPlay = true
      this.capture('demo_video_play')
    } else if (this.hasEnded || this.player.currentTime < 1) {
      this.replayCount += 1
      this.capture('demo_video_replay', { count: this.replayCount })
    } else {
      this.capture('demo_video_resume', { percent: this.currentPercent() })
    }
    this.hasEnded = false
    this.lastTickMs = 0
  }

  /** Report a deliberate pause, ignoring the one the browser fires at the natural end of the clip. */
  private handlePause(): void {
    if (this.player.ended) {
      return
    }
    this.capture('demo_video_pause', { percent: this.currentPercent() })
    this.flushWatchTime()
  }

  /** Remember the clip reached its end, so the next play press counts as a replay. */
  private handleEnded(): void {
    this.hasEnded = true
    this.flushWatchTime()
  }

  /** Accumulate watch time, then emit the progress thresholds and the completion event. */
  private handleTimeUpdate(): void {
    const nowMs: number = Date.now()
    if (this.lastTickMs) {
      const deltaSeconds: number = (nowMs - this.lastTickMs) / 1000
      if (deltaSeconds > 0 && deltaSeconds < MAX_COUNTED_TICK_SECONDS) {
        this.watchedSeconds += deltaSeconds
      }
    }
    this.lastTickMs = nowMs

    const percent: number = this.currentPercent()
    for (const threshold of PROGRESS_THRESHOLDS) {
      if (percent >= threshold && !this.reachedThresholds.has(threshold)) {
        this.reachedThresholds.add(threshold)
        this.capture('demo_video_progress', { percent: threshold })
      }
    }

    if (percent >= COMPLETE_THRESHOLD_PERCENT && !this.hasFiredComplete) {
      this.hasFiredComplete = true
      this.capture('demo_video_complete')
      this.flushWatchTime()
    }
  }

  /** Record where the jump starts, since `seeked` only exposes the destination. */
  private handleSeeking(): void {
    this.seekFromPercent = this.currentPercent()
  }

  /** Report a real jump in the clip, discarding the seek gap so it never counts as watch time. */
  private handleSeeked(): void {
    const toPercent: number = this.currentPercent()
    this.lastTickMs = 0
    if (Math.abs(toPercent - this.seekFromPercent) < 1) {
      return
    }
    this.capture('demo_video_seek', {
      from_percent: this.seekFromPercent,
      to_percent: toPercent,
      direction: toPercent > this.seekFromPercent ? 'forward' : 'backward',
    })
  }

  /** Report the standard fullscreen transition; iOS Safari has its own webkit events. */
  private handleFullscreenChange(): void {
    this.capture('demo_video_fullscreen', { entered: document.fullscreenElement != null })
  }

  /** Report a mute toggle, ignoring the volume changes that leave the mute state untouched. */
  private handleVolumeChange(): void {
    if (this.player.muted === this.isMuted) {
      return
    }
    this.isMuted = this.player.muted
    this.capture('demo_video_mute', { muted: this.player.muted })
  }
}
