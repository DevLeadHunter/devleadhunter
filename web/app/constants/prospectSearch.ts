import type {
  ProspectSearchCandidateOrigin,
  ProspectSearchCandidateStatus,
  ProspectSearchChannel,
  ProspectSearchChannelOption,
  ProspectSearchEmailProofLevel,
  ProspectSearchRejectReason,
  ProspectSearchResultTabKey,
  ProspectSearchStatus,
  ProspectSearchStopReason,
} from '~/types/ProspectSearch'
import type { SelectFieldOption } from '~/types/SelectField'
import type { StatusPresentation } from '~/types/StatusPresentation'

export const PROSPECT_SEARCH_REQUEST_COST_DOLLARS: number = 0.0015

export const PROSPECT_SEARCH_MAXIMUM_TRADES: number = 6
export const PROSPECT_SEARCH_MAXIMUM_CITIES: number = 20

export const PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH: number = 60

export const PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH: number = 80
export const PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE: number = 50
export const PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE: number = 5
export const PROSPECT_SEARCH_DEFAULT_MINIMUM_RATING: number = 4

export const PROSPECT_SEARCH_NO_MINIMUM_RATING: number = 0

export const PROSPECT_SEARCH_MINIMUM_RATING_OPTIONS: SelectFieldOption<number>[] = [
  { value: PROSPECT_SEARCH_NO_MINIMUM_RATING, label: 'Aucune' },
  { value: 3.5, label: '3,5' },
  { value: 4, label: '4,0' },
  { value: 4.5, label: '4,5' },
]

export const PROSPECT_SEARCH_STATUS_PRESENTATION: Record<ProspectSearchStatus, StatusPresentation> = {
  pending: { label: 'En cours', badgeClass: 'app-badge--progress' },
  running: { label: 'En cours', badgeClass: 'app-badge--progress' },
  waiting_browser: { label: 'Lecture des pages Facebook', badgeClass: 'app-badge--info' },
  completed: { label: 'Terminée', badgeClass: 'app-badge--success' },
  cancelled: { label: 'Arrêtée', badgeClass: '' },
  failed: { label: 'Erreur', badgeClass: 'app-badge--danger' },
}

export const PROSPECT_SEARCH_CHANNEL_LABELS: Record<ProspectSearchChannel, string> = {
  email: 'Par email',
  sms: 'Par SMS',
  email_and_sms: 'Email et portable',
}

export const PROSPECT_SEARCH_CHANNEL_OBJECTIVE_LABELS: Record<ProspectSearchChannel, string> = {
  email: 'joignables par email',
  sms: 'joignables par SMS',
  email_and_sms: 'joignables par email et portable',
}

export const PROSPECT_SEARCH_CHANNEL_OPTIONS: ProspectSearchChannelOption[] = [
  {
    value: 'email',
    label: PROSPECT_SEARCH_CHANNEL_LABELS.email,
    description: 'Un email prouvé pour chaque prospect gardé. Un portable seul est mis de côté.',
    icon: 'i-lucide-mail',
  },
  {
    value: 'sms',
    label: PROSPECT_SEARCH_CHANNEL_LABELS.sms,
    description: 'Un numéro de portable pour chaque prospect gardé. Un email seul est mis de côté.',
    icon: 'i-lucide-smartphone',
  },
  {
    value: 'email_and_sms',
    label: PROSPECT_SEARCH_CHANNEL_LABELS.email_and_sms,
    description: 'Les deux pour chaque prospect gardé. Le canal se choisit ensuite, à la campagne.',
    icon: 'i-lucide-messages-square',
  },
]

export const PROSPECT_SEARCH_RESULT_TAB_ORDER: ProspectSearchResultTabKey[] = [
  'kept',
  'set_aside',
  'to_confirm',
  'needs_browser',
  'discovered',
  'rejected',
  'journal',
]

export const PROSPECT_SEARCH_RESULT_TAB_LABELS: Record<ProspectSearchResultTabKey, string> = {
  kept: 'Gardés',
  set_aside: 'Mis de côté',
  to_confirm: 'À confirmer',
  needs_browser: 'Facebook à lire',
  discovered: 'Non vérifiés',
  rejected: 'Écartés',
  journal: 'Journal',
}

export const PROSPECT_SEARCH_EMPTY_TAB_LABELS: Record<ProspectSearchCandidateStatus, string> = {
  kept: 'Aucun prospect gardé pour cette recherche.',
  set_aside: 'Aucun prospect mis de côté.',
  to_confirm: 'Aucun candidat à confirmer.',
  needs_browser: 'Aucune page Facebook à lire.',
  discovered: 'Aucun candidat en attente de vérification.',
  rejected: 'Aucun candidat écarté.',
}

export const PROSPECT_SEARCH_EMAIL_PROOF_PRESENTATION: Record<ProspectSearchEmailProofLevel, StatusPresentation> = {
  a: { label: 'publié par le pro', badgeClass: 'app-badge--success' },
  b: { label: 'annuaire', badgeClass: 'app-badge--info' },
  c: { label: 'à confirmer', badgeClass: 'app-badge--progress' },
}

export const PROSPECT_SEARCH_ORIGIN_LABELS: Record<ProspectSearchCandidateOrigin, string> = {
  google_local: 'Google',
  facebook_search: 'Facebook',
  registry_rge: 'Registre RGE',
  registry_rbq: 'Registre RBQ',
}

export const PROSPECT_SEARCH_STOP_REASON_LABELS: Record<ProspectSearchStopReason, string> = {
  towns: 'plus de ville à parcourir',
  budget: 'budget de requêtes atteint',
}

export const PROSPECT_SEARCH_REJECT_REASON_ORDER: ProspectSearchRejectReason[] = [
  'has_website',
  'no_contact',
  'wrong_trade',
  'chain',
  'closed',
  'homonym',
  'low_rating',
  'already_known',
  'previously_rejected',
  'do_not_contact',
  'manual',
]

export const PROSPECT_SEARCH_REJECT_REASON_LABELS: Record<ProspectSearchRejectReason, string> = {
  has_website: 'A déjà un site web',
  no_contact: 'Aucun contact trouvé',
  wrong_trade: 'Autre métier',
  chain: 'Chaîne ou franchise',
  closed: 'Fermé',
  homonym: 'Homonyme',
  low_rating: 'Note Google trop basse',
  already_known: 'Déjà dans vos prospects',
  previously_rejected: 'Écarté par une recherche précédente',
  do_not_contact: 'Marqué « ne plus contacter »',
  manual: 'Écarté à la main',
}

/** Reasons a discarded candidate cannot be kept anyway: the business is already one of the user's prospects. */
export const PROSPECT_SEARCH_KNOWN_BUSINESS_REASONS: ProspectSearchRejectReason[] = ['already_known', 'do_not_contact']

export const PROSPECT_SEARCH_EVIDENCE_FACT_LABELS: Record<string, string> = {
  email: 'Email',
  email_dropped: 'Email retiré',
  phone: 'Téléphone',
  website: 'Site web',
  facebook: 'Page Facebook',
  facebook_unread: 'Page Facebook illisible',
  owner: 'Dirigeant',
  registry: 'Numéro de registre',
  chain: 'Chaîne ou franchise',
  closed: 'Fermeture',
}
