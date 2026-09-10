import type { SmsStatus } from '~/services/smsService'

/** Human label for each SMS lifecycle status. */
export const SMS_STATUS_LABELS: Record<SmsStatus, string> = {
  pending: 'En attente',
  sent: 'Envoyé',
  delivered: 'Délivré',
  failed: 'Échoué',
}

/** Badge modifier class for each SMS lifecycle status. */
export const SMS_STATUS_BADGE_CLASS: Record<SmsStatus, string> = {
  pending: 'app-badge--progress',
  sent: 'app-badge--info',
  delivered: 'app-badge--success',
  failed: 'app-badge--danger',
}

/** Human label for the known smsmode delivery-detail tokens. */
const SMS_STATUS_DETAIL_LABELS: Record<string, string> = {
  DELIVERED_TO_NETWORK: 'Remis au réseau opérateur',
  DELIVERED_TO_HANDSET: 'Reçu sur le téléphone',
}

/**
 * Human label for an SMS delivery detail.
 * @param detail - The raw status detail from the provider delivery receipt.
 * @returns The French label when the token is known, the raw detail otherwise.
 */
export function smsStatusDetailLabel(detail: string): string {
  return SMS_STATUS_DETAIL_LABELS[detail] ?? detail
}
