import type { SettingsNavGroup } from '~/types/SettingsNav'
import { EMAIL_TEMPLATES_PAGE_PATH, SMS_SETTINGS_PAGE_PATH } from '~/constants/dashboardPages'

export const SMS_SETTINGS_PAGE_LABEL: string = 'Relance SMS'

export const SMS_SETTINGS_PAGE_LABEL_OUTSIDE_WEBSITES_MODULE: string = 'Expéditeur SMS'

export const SETTINGS_NAV_GROUPS: SettingsNavGroup[] = [
  {
    heading: 'Prospection',
    entries: [
      { to: '/dashboard/settings/sending', label: "Configuration d'envoi", icon: 'i-lucide-mail-open' },
      {
        to: SMS_SETTINGS_PAGE_PATH,
        label: SMS_SETTINGS_PAGE_LABEL,
        labelOutsideWebsitesModule: SMS_SETTINGS_PAGE_LABEL_OUTSIDE_WEBSITES_MODULE,
        icon: 'i-lucide-message-square',
        requiredModuleFeature: 'sms-templates',
      },
      {
        to: EMAIL_TEMPLATES_PAGE_PATH,
        label: "Modèles d'email",
        icon: 'i-lucide-layout-template',
        requiredModuleFeature: 'email-templates',
      },
      {
        to: '/dashboard/settings/video',
        label: 'Vidéo de prospection',
        icon: 'i-lucide-video',
        requiredModuleFeature: 'presenter-video',
      },
      { to: '/dashboard/email-health', label: 'Santé email', icon: 'i-lucide-heart-pulse' },
    ],
  },
  {
    heading: 'Compte',
    entries: [
      { to: '/dashboard/settings/notifications', label: 'Notifications', icon: 'i-lucide-bell' },
      { to: '/dashboard/credits', label: 'Mes crédits', icon: 'i-lucide-coins' },
      { to: '/dashboard/settings/billing', label: 'Facturation & paiement', icon: 'i-lucide-receipt' },
    ],
  },
  {
    heading: 'Aide',
    entries: [{ to: '/dashboard/support', label: 'Support', icon: 'i-lucide-life-buoy' }],
  },
  {
    heading: 'Administration',
    adminOnly: true,
    entries: [
      { to: '/dashboard/users', label: 'Utilisateurs', icon: 'i-lucide-users', superAdminOnly: true },
      {
        to: '/dashboard/credit-settings',
        label: 'Crédits & commission',
        icon: 'i-lucide-sliders-horizontal',
        superAdminOnly: true,
      },
      { to: '/dashboard/admin/modules', label: 'Modules', icon: 'i-lucide-blocks', superAdminOnly: true },
      { to: '/dashboard/admin/monitoring', label: 'Monitoring', icon: 'i-lucide-activity' },
      { to: '/dashboard/admin/storage', label: 'Stockage', icon: 'i-lucide-hard-drive' },
      { to: '/dashboard/accounting', label: 'Comptabilité', icon: 'i-lucide-calculator', superAdminOnly: true },
    ],
  },
]
