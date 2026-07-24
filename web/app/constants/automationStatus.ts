import type { AutomationStatus } from '~/types/Automation'
import type { StatusPresentation } from '~/types/StatusPresentation'

export const AUTOMATION_STATUS_PRESENTATION: Record<AutomationStatus, StatusPresentation> = {
  draft: { label: 'Brouillon', badgeClass: '' },
  running: { label: 'En cours', badgeClass: 'app-badge--progress' },
  paused: { label: 'En pause', badgeClass: '' },
  awaiting_review: { label: 'À valider', badgeClass: 'app-badge--info' },
  completed: { label: 'Terminée', badgeClass: 'app-badge--success' },
  cancelled: { label: 'Annulée', badgeClass: 'app-badge--danger' },
  failed: { label: 'Échec', badgeClass: 'app-badge--danger' },
}
