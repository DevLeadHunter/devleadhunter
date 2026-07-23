import type { Prospect } from '~/types'
import type { SendEmailPrefill } from '~/types/DrawerStack'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiSendEmailDrawerProps = UiDrawerProps & {
  prospect?: Prospect | null
  prefill?: SendEmailPrefill | null
}
