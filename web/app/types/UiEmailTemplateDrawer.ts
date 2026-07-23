import type { EmailTemplate } from '~/types'
import type { EmailTemplateDrawerMode } from '~/types/DrawerStack'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiEmailTemplateDrawerProps = UiDrawerProps & {
  mode?: EmailTemplateDrawerMode
  template?: EmailTemplate | null
}

/** Local shape of the template form. */
export type EmailTemplateForm = {
  name: string
  subject: string
  body_html: string
  is_active: boolean
  signature_id: number | null
}
