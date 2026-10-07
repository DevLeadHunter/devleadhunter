import type { Prospect } from '~/types'

export type UiProspectDismissedTableProps = {
  prospects: Prospect[]
  restoringProspectIds: number[]
}

export type UiProspectDismissedTableEmits = {
  open: [prospect: Prospect]
  restore: [prospect: Prospect]
}
