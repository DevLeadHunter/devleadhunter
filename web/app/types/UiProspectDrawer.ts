import type { Prospect } from '~/types'

export type UiProspectDrawerProps = {
  open: boolean
  prospect: Prospect | null
  showBack?: boolean
}
