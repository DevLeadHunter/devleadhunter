import type {
  CampaignResultsFilterKey,
  CampaignResultsProspectState,
  CampaignResultsReplyChannel,
  CampaignResultsReplyVerdict,
} from '~/types/CampaignResults'
import type { UiUnitChartTone } from '~/types/UiUnitChart'

export const CAMPAIGN_RESULTS_STATE_ORDER: CampaignResultsProspectState[] = [
  'sold',
  'interested',
  'replied',
  'visited',
  'refused',
  'silent',
  'pending',
  'not_sent',
]

export const CAMPAIGN_RESULTS_STATE_LABELS: Record<CampaignResultsProspectState, string> = {
  sold: 'Vendu',
  interested: 'Intéressé',
  replied: 'A répondu',
  visited: 'A visité',
  refused: 'Refus',
  silent: 'Sans réaction',
  pending: 'Pas encore contacté',
  not_sent: 'Non envoyé',
}

export const CAMPAIGN_RESULTS_STATE_GROUP_LABELS: Record<CampaignResultsProspectState, string> = {
  sold: 'Ventes',
  interested: 'Intéressés',
  replied: 'Autres réponses',
  visited: 'Ont visité sans écrire',
  refused: 'Refus',
  silent: 'Sans réaction',
  pending: 'Pas encore contactés',
  not_sent: 'Non envoyés',
}

export const CAMPAIGN_RESULTS_STATE_TONES: Record<CampaignResultsProspectState, UiUnitChartTone> = {
  sold: 'ink',
  interested: 'green',
  replied: 'violet',
  visited: 'blue',
  refused: 'red',
  silent: 'neutral',
  pending: 'outline',
  not_sent: 'dashed',
}

export const CAMPAIGN_RESULTS_STATE_TEXT_CLASSES: Record<CampaignResultsProspectState, string> = {
  sold: 'font-medium text-[var(--app-ink)]',
  interested: 'font-medium text-[var(--app-green)]',
  replied: 'font-medium text-[var(--app-violet)]',
  visited: 'font-medium text-[var(--app-blue)]',
  refused: 'font-medium text-[var(--app-red)]',
  silent: 'font-medium text-[var(--app-ink-soft)]',
  pending: 'text-[var(--app-ink-soft)]',
  not_sent: 'text-[var(--app-ink-soft)]',
}

export const CAMPAIGN_RESULTS_FILTER_BY_STATE: Record<CampaignResultsProspectState, CampaignResultsFilterKey> = {
  sold: 'all',
  interested: 'replied',
  replied: 'replied',
  visited: 'toRelaunch',
  refused: 'replied',
  silent: 'silent',
  pending: 'pending',
  not_sent: 'pending',
}

export const CAMPAIGN_RESULTS_FILTER_LABELS: Record<CampaignResultsFilterKey, string> = {
  all: 'Tous',
  opened: 'Ont ouvert leur site',
  toRelaunch: 'À relancer',
  replied: 'Ont répondu',
  silent: 'Sans réaction',
  pending: 'Pas encore contactés',
}

export const CAMPAIGN_RESULTS_VERDICT_LABELS: Record<CampaignResultsReplyVerdict, string> = {
  interested: 'Intéressé',
  refused: 'Refus',
  other: 'Réponse',
}

export const CAMPAIGN_RESULTS_VERDICT_BADGE_CLASSES: Record<CampaignResultsReplyVerdict, string> = {
  interested: 'app-badge--success',
  refused: 'app-badge--danger',
  other: 'app-badge--engaged',
}

export const CAMPAIGN_RESULTS_VERDICT_DOT_CLASSES: Record<CampaignResultsReplyVerdict, string> = {
  interested: 'bg-[var(--app-green)]',
  refused: 'bg-[var(--app-red)]',
  other: 'bg-[var(--app-violet)]',
}

export const CAMPAIGN_RESULTS_CHANNEL_LABELS: Record<CampaignResultsReplyChannel, string> = {
  email: 'Par mail',
  banner: 'Sur son site, par le bandeau',
  manual: 'Ajoutée à la main',
}

export const CAMPAIGN_RESULTS_JOURNEY_WIDTH: number = 280
