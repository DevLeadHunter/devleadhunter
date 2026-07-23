import type { SettingsNavGroup } from '~/types/SettingsNav'

export const SETTINGS_NAV_GROUPS: SettingsNavGroup[] = [
  {
    heading: 'Crédits',
    entries: [
      { kind: 'link', to: '/dashboard/credits', label: 'Mes crédits', icon: 'i-lucide-coins' },
      { kind: 'link', to: '/dashboard/buy-credits', label: 'Acheter des crédits', icon: 'i-lucide-credit-card' },
      {
        kind: 'link',
        to: '/dashboard/credit-settings',
        label: 'Paramètres des crédits',
        icon: 'i-lucide-sliders-horizontal',
        adminOnly: true,
      },
    ],
  },
  {
    heading: 'Démarrage',
    entries: [{ kind: 'link', to: '/configuration', label: 'Mise en route', icon: 'i-lucide-rocket' }],
  },
  {
    heading: 'Envoi',
    entries: [
      { kind: 'link', to: '/dashboard/settings/sending', label: "Configuration d'envoi", icon: 'i-lucide-mail-open' },
      { kind: 'action', action: 'send-policy', label: "Réglages d'envoi", icon: 'i-lucide-sliders-horizontal' },
      { kind: 'link', to: '/dashboard/settings/video', label: 'Vidéo de prospection', icon: 'i-lucide-video' },
    ],
  },
  {
    heading: 'Emails',
    entries: [
      { kind: 'link', to: '/dashboard/email-templates', label: "Modèles d'email", icon: 'i-lucide-layout-template' },
      { kind: 'link', to: '/dashboard/email-health', label: 'Santé email', icon: 'i-lucide-heart-pulse' },
    ],
  },
  {
    heading: 'Aide',
    entries: [{ kind: 'link', to: '/dashboard/support', label: 'Support', icon: 'i-lucide-life-buoy' }],
  },
  {
    heading: 'Administration',
    adminOnly: true,
    entries: [
      { kind: 'link', to: '/dashboard/users', label: 'Utilisateurs', icon: 'i-lucide-users' },
      { kind: 'link', to: '/dashboard/admin/monitoring', label: 'Monitoring', icon: 'i-lucide-activity' },
      { kind: 'link', to: '/dashboard/admin/storage', label: 'Stockage', icon: 'i-lucide-hard-drive' },
      { kind: 'link', to: '/dashboard/accounting', label: 'Comptabilité', icon: 'i-lucide-calculator' },
    ],
  },
]
