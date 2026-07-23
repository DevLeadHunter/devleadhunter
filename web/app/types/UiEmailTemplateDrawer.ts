import type { EmailTemplate } from '~/types'
import type { EmailTemplateDrawerMode } from '~/types/DrawerStack'
import type { UiDrawerProps } from '~/types/UiDrawer'

export type UiEmailTemplateDrawerProps = UiDrawerProps & {
  mode?: EmailTemplateDrawerMode
  template?: EmailTemplate | null
}
