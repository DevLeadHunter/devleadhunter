import type { FullVideoBuildResult } from '~/services/storyblokSidecarService'

export type DesktopVideoSubjectKind = 'site' | 'assistant'

export type DesktopVideoRequest = {
  kind: DesktopVideoSubjectKind
  subjectId: number
  businessName: string
  requestedAt: string
}

export type DesktopVideoSubjectRelay = {
  describeVideo: (businessName: string) => string
  claim: (subjectId: number) => Promise<void>
  build: (subjectId: number) => Promise<FullVideoBuildResult>
  reportFailure: (subjectId: number, message: string) => Promise<void>
}
