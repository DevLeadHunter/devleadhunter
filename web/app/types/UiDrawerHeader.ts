export type UiDrawerHeaderProps = {
  title: string
  icon: string
  subtitle?: string
  showBack: boolean
  titleId?: string
}

export type UiDrawerHeaderEmits = {
  back: []
  close: []
}
