import type { UiMobileTabBarLink, UiMobileTabBarPagePlacement } from '~/types/UiMobileTabBar'
import type { DlhModulePrimaryCta, UiSidebarCounterKey } from '~/types/UiSidebar'
import {
  CAMPAIGNS_PAGE_PATH,
  EMAIL_TRACKING_PAGE_PATH,
  NOTIFICATIONS_PAGE_PATH,
  SMS_TRACKING_PAGE_PATH,
} from '~/constants/dashboardPages'
import { WEBSITES_DASHBOARD_PATH } from '~/constants/productModules'
import { MY_PROSPECTS_PAGE_PATH, PROSPECT_SEARCH_PAGE_PATH } from '~/constants/prospectSearch'

export const MOBILE_TAB_BAR_MAXIMUM_PHONE_LINK_COUNT: number = 4

export const MOBILE_TAB_BAR_MAXIMUM_TABLET_LINK_COUNT: number = 6

export const MOBILE_TAB_BAR_UNREAD_NOTIFICATIONS_COUNTER_KEY: UiSidebarCounterKey = 'unreadNotifications'

export const MOBILE_TAB_BAR_NOTIFICATIONS_LINK: UiMobileTabBarLink = {
  to: NOTIFICATIONS_PAGE_PATH,
  icon: 'i-lucide-bell',
  label: 'Notifications',
  caption: null,
  counterKey: MOBILE_TAB_BAR_UNREAD_NOTIFICATIONS_COUNTER_KEY,
  isShownOnPhone: true,
}

export const MOBILE_TAB_BAR_CAPTIONS: Record<string, string> = {
  [WEBSITES_DASHBOARD_PATH]: 'Accueil',
  [EMAIL_TRACKING_PAGE_PATH]: 'Emails',
  [SMS_TRACKING_PAGE_PATH]: 'SMS',
  [MY_PROSPECTS_PAGE_PATH]: 'Prospects',
}

export const MOBILE_TAB_BAR_SHARED_PROSPECTING_PAGE_PATHS: string[] = [
  CAMPAIGNS_PAGE_PATH,
  EMAIL_TRACKING_PAGE_PATH,
  SMS_TRACKING_PAGE_PATH,
  MY_PROSPECTS_PAGE_PATH,
]

export const MOBILE_TAB_BAR_WEBSITES_PAGE_PLACEMENTS: UiMobileTabBarPagePlacement[] = [
  { to: WEBSITES_DASHBOARD_PATH, isShownOnPhone: false },
  { to: CAMPAIGNS_PAGE_PATH, isShownOnPhone: true },
  { to: NOTIFICATIONS_PAGE_PATH, isShownOnPhone: true },
  { to: EMAIL_TRACKING_PAGE_PATH, isShownOnPhone: true },
  { to: SMS_TRACKING_PAGE_PATH, isShownOnPhone: true },
  { to: MY_PROSPECTS_PAGE_PATH, isShownOnPhone: false },
]

export const MOBILE_TAB_BAR_WEBSITES_MAIN_ACTION: DlhModulePrimaryCta = {
  label: 'Rechercher des leads',
  to: PROSPECT_SEARCH_PAGE_PATH,
  icon: 'i-lucide-search',
}
