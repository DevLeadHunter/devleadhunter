import type { ProspectionScriptModule } from '~/composables/useProspectionScript'

export type PresenterVideoRecordingGuideProps = {
  module: ProspectionScriptModule
  isImporting: boolean
}

export type PresenterVideoGuideStep = {
  title: string
  detail: string
}

export type PresenterVideoSpeechLine = {
  timing: string
  role: string
  text: string
}
