export type UiRemovableChipListProps = {
  labels: string[]
  disabled?: boolean
}

export type UiRemovableChipListEmits = {
  remove: [label: string]
}
