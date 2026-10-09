/** What a requested video films: a demo site or a receptionist, named like the API's kinds of video. */
export type DesktopVideoSubjectKind = 'site' | 'assistant'

/** A video another device asked this computer to build, whatever it films. */
export type DesktopVideoRequest = {
  kind: DesktopVideoSubjectKind
  subjectId: number
  businessName: string
  requestedAt: string
}

export type DesktopVideoBuildStatus = 'done' | 'needs_login' | 'unavailable' | 'failed'

/** How the local build of a requested video ended, with a message when it failed. */
export type DesktopVideoBuildOutcome = {
  status: DesktopVideoBuildStatus
  message?: string
}

/** How this computer takes, builds and gives up the videos of one kind of subject. */
export type DesktopVideoSubjectRelay = {
  describeVideo: (businessName: string) => string
  claim: (subjectId: number) => Promise<void>
  build: (subjectId: number) => Promise<DesktopVideoBuildOutcome>
  reportFailure: (subjectId: number, message: string) => Promise<void>
}
