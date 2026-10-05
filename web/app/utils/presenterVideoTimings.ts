import type { PresenterVideoTake } from '~/types/PresenterVideoTake'
import type { PreviewTimingOverrides } from '~/services/storyblokSidecarService'
import type { AssistantPreviewTimingOverrides } from '~/types/AssistantSidecar'

/** Mirror of the server's automatic split: Storyblok budget carved out of the middle. */
export const AUTO_STORYBLOK_SECONDS: number = 17

/** Mirror of the server's floor for the site-scroll part. */
export const MIN_SITE_SCROLL_SECONDS: number = 6

/** Under this, the scripted Storyblok edit demo gets visibly cut. */
export const STORYBLOK_COMFORT_SECONDS: number = 10

/** Mirror of the server's client-space chapter, which closes the receptionist's middle. */
export const RECEPTIONIST_SPACE_CHAPTER_SECONDS: number = 7

/** Mirror of the server's shortest chat scene: below it plus the chapter, the chapter is dropped. */
export const MIN_WIDGET_SCENE_SECONDS: number = 6

/** Below this gap, a cut point read back from the database has not moved (FLOAT columns add noise). */
export const CUT_POINT_TOLERANCE_SECONDS: number = 0.01

/** Where a take's video parts fall, computed like the server does before a montage. */
export class PresenterVideoTimings {
  /**
   * Whether two cut points are the same once the noise of the database is ignored.
   * @param firstSeconds - A cut point, or null for the automatic split.
   * @param secondSeconds - The other cut point.
   * @returns True when they would give the same video.
   */
  static isSameCutPoint(firstSeconds: number | null, secondSeconds: number | null): boolean {
    if (firstSeconds === null || secondSeconds === null) return firstSeconds === secondSeconds
    return Math.abs(firstSeconds - secondSeconds) <= CUT_POINT_TOLERANCE_SECONDS
  }

  /**
   * Whether two versions of a take cut the video at the same places.
   * @param firstTake - A version of the take.
   * @param secondTake - The other version.
   * @returns True when their intro, outro and site part match.
   */
  static haveSameCutPoints(firstTake: PresenterVideoTake, secondTake: PresenterVideoTake): boolean {
    return (
      PresenterVideoTimings.isSameCutPoint(firstTake.intro_seconds, secondTake.intro_seconds) &&
      PresenterVideoTimings.isSameCutPoint(firstTake.outro_seconds, secondTake.outro_seconds) &&
      PresenterVideoTimings.isSameCutPoint(firstTake.site_seconds, secondTake.site_seconds)
    )
  }

  /**
   * Seconds between intro and outro, shared by what the video shows in the middle.
   * @param durationSeconds - Length of the whole take.
   * @param introSeconds - Full-screen webcam seconds at the start.
   * @param outroSeconds - Full-screen webcam seconds at the end.
   * @returns The middle length, never negative.
   */
  static middleSeconds(durationSeconds: number, introSeconds: number, outroSeconds: number): number {
    return Math.max(0, durationSeconds - introSeconds - outroSeconds)
  }

  /**
   * Site-scroll seconds the server uses while no split is saved: the middle minus the Storyblok budget.
   * @param middleSeconds - The take's middle length.
   * @returns The automatic site part, floored like the server does.
   */
  static automaticSiteSeconds(middleSeconds: number): number {
    return Math.max(MIN_SITE_SCROLL_SECONDS, Math.round((middleSeconds - AUTO_STORYBLOK_SECONDS) * 2) / 2)
  }

  /**
   * Site-scroll seconds a real generation would use with this take.
   * @param take - The take.
   * @returns The saved split when there is one, else the automatic one, kept inside the middle.
   */
  static siteSeconds(take: PresenterVideoTake): number {
    const middle: number = PresenterVideoTimings.middleSeconds(
      take.duration_seconds,
      take.intro_seconds,
      take.outro_seconds,
    )
    const wanted: number = take.site_seconds ?? PresenterVideoTimings.automaticSiteSeconds(middle)
    return Math.min(Math.max(wanted, MIN_SITE_SCROLL_SECONDS), middle)
  }

  /**
   * Timings a site video build needs to be montaged with this take rather than the one in use.
   * @param take - The take montaged.
   * @returns The build's timing fields.
   */
  static siteBuildTimings(take: PresenterVideoTake): PreviewTimingOverrides {
    return {
      presenter_duration: take.duration_seconds,
      presenter_intro: take.intro_seconds,
      presenter_outro: take.outro_seconds,
      site_seconds: PresenterVideoTimings.siteSeconds(take),
      total_seconds: PresenterVideoTimings.middleSeconds(take.duration_seconds, take.intro_seconds, take.outro_seconds),
    }
  }

  /**
   * Timings a receptionist video build needs to be montaged with this take rather than the one in use.
   * @param take - The take montaged.
   * @returns The build's timing fields.
   */
  static receptionistBuildTimings(take: PresenterVideoTake): AssistantPreviewTimingOverrides {
    return {
      presenter_duration: take.duration_seconds,
      presenter_intro: take.intro_seconds,
      presenter_outro: take.outro_seconds,
      total_seconds: PresenterVideoTimings.middleSeconds(take.duration_seconds, take.intro_seconds, take.outro_seconds),
    }
  }

  /**
   * Seconds of the receptionist's middle given to the client space, 0 when the chat would be left too short.
   * @param middleSeconds - The take's middle length.
   * @returns The chapter length.
   */
  static receptionistSpaceChapterSeconds(middleSeconds: number): number {
    return middleSeconds >= MIN_WIDGET_SCENE_SECONDS + RECEPTIONIST_SPACE_CHAPTER_SECONDS
      ? RECEPTIONIST_SPACE_CHAPTER_SECONDS
      : 0
  }

  /**
   * Format a segment length for the timeline and its legend.
   * @param seconds - Segment length.
   * @returns A short label (e.g. « 4,5 s »).
   */
  static formatSeconds(seconds: number): string {
    return `${seconds.toFixed(1).replace(/\.0$/, '').replace('.', ',')} s`
  }
}
