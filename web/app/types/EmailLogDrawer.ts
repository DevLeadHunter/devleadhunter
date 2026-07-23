import type { EmailLog } from '~/types'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type EmailLogDrawerProps = UiDrawerProps & {
  log: EmailLog | null
  campaignName?: string
}
