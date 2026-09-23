import type { DlhModule, UiSidebarGroup } from '~/types/UiSidebar'

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
      { to: '/dashboard/my-prospects', label: 'Mes prospects', icon: 'i-lucide-users' },
      { to: '/dashboard/coverage', label: 'Carte de prospection', icon: 'i-lucide-map' },
      { to: '/dashboard/demo-sites', label: 'Sites démo', icon: 'i-lucide-app-window' },
      { to: '/dashboard/campaigns', label: 'Campagnes', icon: 'i-lucide-megaphone' },
      { to: '/dashboard/emails', label: 'Suivi des emails', icon: 'i-lucide-send' },
      { to: '/dashboard/sms', label: 'Suivi des SMS', icon: 'i-lucide-message-square-text' },
      { to: '/dashboard/orders', label: 'Ventes', icon: 'i-lucide-banknote' },
    ],
  },
]

/**
 * The AI-assistant module navigation: the same prospection base, but the deliverable is an
 * embedded receptionist (« Assistants IA ») instead of a demo site — so « Sites démo » and
 * the site automation tunnel drop out, the assistants + their captured leads come in, and the
 * one-off « Ventes » becomes the recurring « Abonnements ».
 */
const AI_ASSISTANT_NAV: UiSidebarGroup[] = [
  {
    heading: 'Pilotage',
    links: [{ to: '/dashboard', label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' }],
  },
  {
    heading: 'Prospection',
    links: [
      { to: '/dashboard/my-prospects', label: 'Mes prospects', icon: 'i-lucide-users' },
      { to: '/dashboard/coverage', label: 'Carte de prospection', icon: 'i-lucide-map' },
      { to: '/dashboard/ai-assistants', label: 'Assistants IA', icon: 'i-lucide-bot' },
      { to: '/dashboard/campaigns', label: 'Campagnes', icon: 'i-lucide-megaphone' },
      { to: '/dashboard/emails', label: 'Suivi des emails', icon: 'i-lucide-send' },
      { to: '/dashboard/sms', label: 'Suivi des SMS', icon: 'i-lucide-message-square-text' },
      { to: '/dashboard/subscriptions', label: 'Abonnements', icon: 'i-lucide-repeat' },
    ],
  },
]

/** Every product module of the shell, in switcher order. Locked ones announce their arrival. */
export const DASHBOARD_MODULES: DlhModule[] = [
  {
    key: 'websites',
    label: 'Sites web',
    icon: 'i-lucide-globe',
    locked: false,
    home: '/dashboard',
    primaryCta: { label: 'Créer une automatisation', to: '/dashboard/automations/new', icon: 'i-lucide-plus' },
    navGroups: WEBSITES_NAV,
  },
  {
    key: 'ai-assistant',
    label: 'Assistant IA',
    icon: 'i-lucide-bot',
    locked: false,
    home: '/dashboard/ai-assistants',
    primaryCta: { label: 'Trouver des prospects', to: '/dashboard/search-prospects', icon: 'i-lucide-search' },
    navGroups: AI_ASSISTANT_NAV,
  },
  {
    key: 'wallet-cards',
    label: 'Cartes Apple Wallet',
    icon: 'i-lucide-wallet-cards',
    locked: true,
    home: '/dashboard',
    primaryCta: null,
    navGroups: [],
  },
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
export const DEFAULT_MODULE_KEY: DlhModule['key'] = 'websites'
