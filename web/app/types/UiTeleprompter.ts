export type UiTeleprompterVariant = 'card' | 'overlay'

export type UiTeleprompterProps = {
  text: string
  isRunning: boolean
  restartToken: number
  variant?: UiTeleprompterVariant
}
