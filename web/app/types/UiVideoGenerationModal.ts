/** Lifecycle of one step in the video-generation progress modal. */
export type VideoGenerationStepState = 'pending' | 'active' | 'done' | 'error'

/** One row of the progress modal's step list. */
export type VideoGenerationStep = {
  key: string
  label: string
  state: VideoGenerationStepState
}

export type UiVideoGenerationModalProps = {
  open: boolean
  title: string
  steps: VideoGenerationStep[]
  logLines: string[]
  elapsedSeconds: number
  errorMessage: string
  /** While true the close button reads « Masquer » — the build keeps running. */
  isRunning: boolean
}

export type UiVideoGenerationModalEmits = {
  close: []
}
