import type { Prospect } from '~/types'

export type UiProspectTableProps = {
  prospects: Prospect[]
  selectedProspects?: string[]
}

export type UiProspectTableEmits = {
  viewProspect: [prospect: Prospect]
  deleteProspect: [prospect: Prospect]
  toggleSelect: [prospect: Prospect]
  toggleSelectAll: [checked: boolean]
}
