import type { DemoSiteWithdrawn } from '~/types/demoSite'

export type DemoOfflinePageProps = {
  slug: string
  withdrawnDemo: DemoSiteWithdrawn | null
}

export type DemoRevivalState = 'idle' | 'reviving' | 'failed'

export type DemoOwnerContactChannel = 'phone' | 'email'
