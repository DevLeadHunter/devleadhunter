/**
 * Props of the recording teleprompter.
 * @module types/UiTeleprompter
 */

export interface UiTeleprompterProps {
  /** Full text of the take being read. */
  text: string
  /** Whether the highlight advances on its own (i.e. the camera is rolling). */
  isRunning: boolean
  /** Bump this to restart the reading from the first beat. */
  restartToken: number
}
