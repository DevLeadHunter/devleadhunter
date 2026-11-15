import type { DlhModule, DlhModuleKey, UiSidebarGroup } from '~/types/UiSidebar'
import {
  CAMPAIGNS_PAGE_PATH,
  DEMO_SITES_PAGE_PATH,
  EMAIL_TRACKING_PAGE_PATH,
  SMS_TRACKING_PAGE_PATH,
} from '~/constants/dashboardPages'
import { WEBSITES_DASHBOARD_PATH, WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { MY_PROSPECTS_PAGE_PATH, PROSPECT_SEARCH_PENDING_LEADS_COUNTER_KEY } from '~/constants/prospectSearch'

/**
 * The site-web module navigation: find prospects, build them a demo site, sell it.
 * This is the historical DevLeadHunter experience, kept exactly as it was.
 */
const WEBSITES_NAV: UiSidebarGroup[] = [
  {
    heading: 'Pilotage',
    links: [
      { to: WEBSITES_DASHBOARD_PATH, label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' },
      { to: '/dashboard/automations', label: 'Automatisations', icon: 'i-lucide-workflow' },
    ],
  },
  {
    heading: 'Prospection',
    links: [
      {
        to: MY_PROSPECTS_PAGE_PATH,
        label: 'Mes prospects',
        icon: 'i-lucide-users',
        counterKey: PROSPECT_SEARCH_PENDING_LEADS_COUNTER_KEY,
      },
      { to: '/dashboard/coverage', label: 'Carte de prospection', icon: 'i-lucide-map' },
      { to: DEMO_SITES_PAGE_PATH, label: 'Sites démo', icon: 'i-lucide-app-window' },
      { to: CAMPAIGNS_PAGE_PATH, label: 'Campagnes', icon: 'i-lucide-megaphone' },
      { to: EMAIL_TRACKING_PAGE_PATH, label: 'Suivi des emails', icon: 'i-lucide-send' },
      { to: SMS_TRACKING_PAGE_PATH, label: 'Suivi des SMS', icon: 'i-lucide-message-square-text' },
      { to: '/dashboard/orders', label: 'Ventes', icon: 'i-lucide-banknote' },
    ],
  },
]

/** The core's module, first in the switcher and always available. */
export const WEBSITES_DASHBOARD_MODULE: DlhModule = {
  key: WEBSITES_MODULE_KEY,
  label: 'Sites web',
  icon: 'i-lucide-globe',
  locked: false,
  home: WEBSITES_DASHBOARD_PATH,
  primaryCta: { label: 'Créer une automatisation', to: '/dashboard/automations/new', icon: 'i-lucide-plus' },
  tabBarMainAction: null,
  navGroups: WEBSITES_NAV,
}

/** The default module when nothing is stored yet (the historical experience). */
export const DEFAULT_MODULE_KEY: DlhModuleKey = WEBSITES_MODULE_KEY
