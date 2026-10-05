import type { ProspectionScriptModule } from '~/composables/useProspectionScript'
import type { PresenterVideoTake } from '~/types/PresenterVideoTake'

export type PresenterVideoCaptureMode = 'record' | 'import'

export type PresenterVideoCaptureOption = {
  mode: PresenterVideoCaptureMode
  icon: string
  title: string
  detail: string
  badge: string
}

export type PresenterVideoTakeCaptureProps = {
  module: ProspectionScriptModule
  autoGenerate: boolean
  canGoBackToTakes: boolean
}

export type PresenterVideoTakeCaptureEmits = {
  saved: [take: PresenterVideoTake]
  'back-to-takes': []
}
