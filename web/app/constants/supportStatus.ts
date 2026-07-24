import type { StatusPresentation } from '~/types/StatusPresentation'

export const SUPPORT_STATUS_PRESENTATION: Record<string, StatusPresentation> = {
  open: { label: 'Ouvert', badgeClass: 'app-badge--progress' },
  waiting_support: { label: 'Attente support', badgeClass: 'app-badge--progress' },
  waiting_user: { label: 'Attente client', badgeClass: '' },
  resolved: { label: 'Résolu', badgeClass: 'app-badge--success' },
  closed: { label: 'Fermé', badgeClass: '' },
}
