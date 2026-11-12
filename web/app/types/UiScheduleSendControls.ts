export type UiScheduleSendControlsProps = {
  canSend: boolean
  isBusy: boolean
  sendLabel: string
}

export type UiScheduleSendControlsEmits = {
  send: []
  schedule: [moment: Date]
}
