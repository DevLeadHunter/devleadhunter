/**
 * Props and internal shapes of the in-app presenter-clip recorder.
 */

import type { ProspectionScriptModule } from '~/composables/useProspectionScript'
import type { RecordedTake } from '~/composables/useWebcamRecorder'

export type UiPresenterVideoRecorderProps = {
  autoGenerate: boolean
  /** Which module's clip is filmed (the site clip by default): each module has its own takes. */
  module: ProspectionScriptModule
}

/** Where the recorder is in the take-after-take flow. */
export type RecorderPhase = 'permission' | 'setup' | 'countdown' | 'recording' | 'review' | 'ready'

/** A take that has been kept, paired with the segment it fills. */
export type KeptTake = {
  take: RecordedTake
  seconds: number
}
