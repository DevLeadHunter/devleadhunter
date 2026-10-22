/** French label of each Gmail sender requirement Postmaster checks. */
export const POSTMASTER_REQUIREMENT_LABELS: Record<string, string> = {
  SPF: 'SPF',
  DKIM: 'DKIM',
  SPF_AND_DKIM: 'SPF et DKIM',
  DMARC_POLICY: 'Politique DMARC',
  DMARC_ALIGNMENT: 'Alignement DMARC',
  MESSAGE_FORMATTING: 'Format des messages',
  DNS_RECORDS: 'Enregistrements DNS',
  ENCRYPTION: 'Chiffrement TLS',
  USER_REPORTED_SPAM_RATE: 'Taux de spam signalé',
  ONE_CLICK_UNSUBSCRIBE: 'Désinscription en un clic',
  HONOR_UNSUBSCRIBE: 'Désinscriptions respectées',
}

/** French label of a compliance status. */
export const POSTMASTER_STATUS_LABELS: Record<string, string> = {
  COMPLIANT: 'Conforme',
  NEEDS_WORK: 'À corriger',
}

/** Colour of a compliance status. */
export const POSTMASTER_STATUS_COLORS: Record<string, string> = {
  COMPLIANT: 'var(--app-green)',
  NEEDS_WORK: 'var(--app-red)',
}

/** What Gmail's deliverability verdict reason means, in plain words. */
export const POSTMASTER_DELIVERABILITY_REASON_LABELS: Record<string, string> = {
  MESSAGE_VOLUME_LOW: 'Pas encore assez de mails envoyés vers Gmail pour en juger.',
  SMTP_ERRORS_HIGH: 'Beaucoup de mails refusés à la livraison.',
  SENDER_NOT_COMPLIANT: "Une exigence de Gmail n'est pas remplie.",
  SPAM_RATE_HIGH: 'Le taux de spam dépasse 0,1 %.',
  USER_FEEDBACK_NEGATIVE: 'Les destinataires ne veulent pas de ces mails.',
  USER_FEEDBACK_LOW: 'Les destinataires réagissent peu à ces mails.',
  USER_FEEDBACK_POSITIVE: 'Les destinataires veulent recevoir ces mails.',
}
