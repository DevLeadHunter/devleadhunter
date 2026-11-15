import type { DlhModulePrimaryCta, UiSidebarCounterKey } from '~/types/UiSidebar'

export type UiMobileTabBarLink = {
  to: string
  icon: string
  label: string
  caption: string | null
  counterKey: UiSidebarCounterKey | null
  isShownOnPhone: boolean
}

export type UiMobileTabBarNavigation = {
  links: UiMobileTabBarLink[]
  mainAction: DlhModulePrimaryCta | null
}

export type UiMobileTabBarPagePlacement = {
  to: string
  isShownOnPhone: boolean
}
