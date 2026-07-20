/**
 * Props and internal shapes of the in-app presenter-clip recorder.
 * @module types/UiPresenterVideoRecorder
 */

import type { RecordedTake } from '~/composables/useWebcamRecorder'

export interface UiPresenterVideoRecorderProps {
  /** Whether new demo sites should generate their video automatically. */
  autoGenerate: boolean
}

/** Where the recorder is in the take-after-take flow. */
export type RecorderPhase = 'permission' | 'setup' | 'countdown' | 'recording' | 'review' | 'ready'

/** A take that has been kept, paired with the segment it fills. */
export interface KeptTake {
  take: RecordedTake
  /** Duration measured in the browser, shown while reviewing. */
  seconds: number
}
