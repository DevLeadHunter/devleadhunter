import type { Prospect } from '~/types'

/** Last-column action rendered for each row. */
export type UiProspectTableRowAction = 'delete' | 'remove'

export type UiProspectTableProps = {
  prospects: Prospect[]
  selectedProspects?: string[]
  /** When true, renders the A/B variant column (values keyed by prospect id). */
  showAbVariant?: boolean
  abVariants?: Record<number, string | null | undefined>
  temperatures?: Record<number, string>
  /** Action button behavior in the last column (default: delete icon). */
  rowAction?: UiProspectTableRowAction
  /** Hide the selection checkbox column. */
  hideSelection?: boolean
  /** Show a drag handle on each row and let the user reorder rows by drag & drop. */
  reorderable?: boolean
}

export type UiProspectTableEmits = {
  viewProspect: [prospect: Prospect]
  editProspect: [prospect: Prospect]
  deleteProspect: [prospect: Prospect]
  removeProspect: [prospect: Prospect]
  toggleSelect: [prospect: Prospect]
  toggleSelectAll: [checked: boolean]
  /** The user dropped a row into a new position — carries every prospect id in the new order. */
  reorder: [orderedProspectIds: number[]]
}
