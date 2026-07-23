import type { Prospect } from '~/types'
import type { SendEmailPrefill } from '~/types/DrawerStack'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiSendEmailDrawerProps = UiDrawerProps & {
  prospect?: Prospect | null
  prefill?: SendEmailPrefill | null
}

/** Local shape of the manual send form. */
export type SendEmailForm = {
  recipient_email: string
  recipient_name: string
  subject: string
  body: string
}
