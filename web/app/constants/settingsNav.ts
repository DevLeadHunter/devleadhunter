import type { SettingsNavGroup } from '~/types/SettingsNav'

export const SETTINGS_NAV_GROUPS: SettingsNavGroup[] = [
  {
    heading: 'Prospection',
    entries: [
      { to: '/dashboard/settings/sending', label: "Configuration d'envoi", icon: 'i-lucide-mail-open' },
      { to: '/dashboard/settings/sms', label: 'Relance SMS', icon: 'i-lucide-message-square' },
      { to: '/dashboard/email-templates', label: "Modèles d'email", icon: 'i-lucide-layout-template' },
      { to: '/dashboard/settings/video', label: 'Vidéo de prospection', icon: 'i-lucide-video' },
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
