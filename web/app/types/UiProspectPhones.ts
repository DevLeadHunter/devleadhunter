import type { Prospect } from '~/types'

export type UiProspectPhonesProps = {
  prospect: Prospect
  editable: boolean
}

export type UiProspectPhonesEmits = {
  updated: [prospect: Prospect]
}
