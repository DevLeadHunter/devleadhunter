export type UiScheduleSendControlsProps = {
  canSend: boolean
  isBusy: boolean
  sendLabel: string
}

export type UiScheduleSendControlsEmits = {
  send: []
  schedule: [moment: Date]
}

/** A one-click send time offered in the schedule panel. */
export type ScheduleSendPreset = {
  key: string
  label: string
  moment: Date
}
