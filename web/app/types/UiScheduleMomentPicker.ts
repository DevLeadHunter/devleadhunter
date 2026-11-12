export type UiScheduleMomentPickerProps = {
  title: string
  isBusy: boolean
  initialMoment: Date | null
}

export type UiScheduleMomentPickerEmits = {
  schedule: [moment: Date]
}

/** A one-click time offered in the schedule panel. */
export type ScheduleSendPreset = {
  key: string
  label: string
  moment: Date
}
