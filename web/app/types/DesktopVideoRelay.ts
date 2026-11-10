import type { FullVideoBuildResult } from '~/services/storyblokSidecarService'
import type { ProductModuleKey } from '~/types/ProductModule'

/** What a desktop video is of: `site` (a demo site), or the kind of demo a product module registers. */
export type DesktopVideoSubjectKind = string

export type DesktopVideoRequest = {
  kind: DesktopVideoSubjectKind
  subjectId: number
  businessName: string
  requestedAt: string
}

/** One kind of demo whose prospection video this computer builds when another device asks for it. */
export type DesktopVideoSubjectRelay = {
  kind: DesktopVideoSubjectKind
  moduleKey: ProductModuleKey
  listWaitingRequests: () => Promise<DesktopVideoRequest[]>
  describeVideo: (businessName: string) => string
  claim: (subjectId: number) => Promise<void>
  build: (subjectId: number) => Promise<FullVideoBuildResult>
  reportFailure: (subjectId: number, message: string) => Promise<void>
}
