import type { DlhModule, DlhModuleKey, UiSidebarGroup } from '~/types/UiSidebar'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'

/**
 * The site-web module navigation: find prospects, build them a demo site, sell it.
 * This is the historical DevLeadHunter experience, kept exactly as it was.
 */
const WEBSITES_NAV: UiSidebarGroup[] = [
  {
    heading: 'Pilotage',
    links: [
      { to: '/dashboard', label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' },
      { to: '/dashboard/automations', label: 'Automatisations', icon: 'i-lucide-workflow' },
    ],
  },
  {
    heading: 'Prospection',
    links: [
      { to: '/dashboard/my-prospects', label: 'Mes prospects', icon: 'i-lucide-users', counterKey: 'pendingLeads' },
      { to: '/dashboard/coverage', label: 'Carte de prospection', icon: 'i-lucide-map' },
      { to: '/dashboard/demo-sites', label: 'Sites démo', icon: 'i-lucide-app-window' },
      { to: '/dashboard/campaigns', label: 'Campagnes', icon: 'i-lucide-megaphone' },
      { to: '/dashboard/emails', label: 'Suivi des emails', icon: 'i-lucide-send' },
      { to: '/dashboard/sms', label: 'Suivi des SMS', icon: 'i-lucide-message-square-text' },
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
  home: '/dashboard',
  primaryCta: { label: 'Créer une automatisation', to: '/dashboard/automations/new', icon: 'i-lucide-plus' },
  navGroups: WEBSITES_NAV,
}

/** A module still to come, last in the switcher: clicking it only announces its arrival. */
export const LOCKED_DASHBOARD_MODULES: DlhModule[] = [
  {
    key: 'freelance-missions',
    label: 'Missions freelance',
    icon: 'i-lucide-briefcase-business',
    locked: true,
    home: '/dashboard',
    primaryCta: null,
    navGroups: [],
  },
]

/** The default module when nothing is stored yet (the historical experience). */
export const DEFAULT_MODULE_KEY: DlhModuleKey = WEBSITES_MODULE_KEY
