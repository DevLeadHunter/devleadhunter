import type { ProspectionScriptModule } from '~/composables/useProspectionScript'
import type { PresenterVideoTake } from '~/types/PresenterVideoTake'
import type { SelectFieldOption } from '~/types/SelectField'

export type PresenterVideoTimingsCardProps = {
  take: PresenterVideoTake
  module: ProspectionScriptModule
  takeOptions: SelectFieldOption<number>[]
  canBuildPreview: boolean
  isBuildRunning: boolean
  isBuildingPreview: boolean
  previewVideoUrl: string | null
}

export type PresenterVideoTimingsCardEmits = {
  'select-take': [takeId: number]
  saved: [take: PresenterVideoTake]
  preview: [take: PresenterVideoTake]
}

/** One part of the video timeline bar (intro, the middle's parts, outro). */
export type PresenterVideoTimelineSegment = {
  key: string
  label: string
  shortLabel: string
  seconds: number
  /** CSS width of the bar segment, proportional to its duration. */
  width: string
  /** Tailwind classes giving the segment its grayscale tone. */
  tone: string
}

export type PresenterVideoTimelinePart = Omit<PresenterVideoTimelineSegment, 'width'>
