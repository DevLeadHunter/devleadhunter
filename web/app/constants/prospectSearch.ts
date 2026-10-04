import type {
  ProspectSearchCandidateOrigin,
  ProspectSearchCandidateStatus,
  ProspectSearchChannel,
  ProspectSearchChannelOption,
  ProspectSearchEmailProofLevel,
  ProspectSearchEmptyLeadsNotice,
  ProspectSearchEmptyLeadsSituation,
  ProspectSearchRejectReason,
  ProspectSearchStatus,
  ProspectSearchStopReason,
  ProspectSearchValidationMode,
  ProspectSearchValidationOption,
} from '~/types/ProspectSearch'
import type { ProspectSearchStepDefinition } from '~/types/ProspectSearchCreatePage'
import type { SelectFieldOption } from '~/types/SelectField'
import type { StatusPresentation } from '~/types/StatusPresentation'

export const PROSPECT_SEARCH_PAGE_PATH: string = '/dashboard/search-prospects'

export const MY_PROSPECTS_PAGE_PATH: string = '/dashboard/my-prospects'

export const PROSPECT_SEARCH_REQUEST_COST_DOLLARS: number = 0.0015

export const PROSPECT_SEARCH_BASE_REQUEST_COUNT: number = 60

export const PROSPECT_SEARCH_REQUESTS_PER_WANTED_PROSPECT: number = 45

export const PROSPECT_SEARCH_DURATION_LABEL: string = '5 à 10 minutes'

export const PROSPECT_SEARCH_MAXIMUM_TRADES: number = 6
export const PROSPECT_SEARCH_MAXIMUM_CITIES: number = 20

export const PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH: number = 60

export const PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH: number = 80
export const PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE: number = 50
export const PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE: number = 5
export const PROSPECT_SEARCH_DEFAULT_MINIMUM_RATING: number = 4

export const PROSPECT_SEARCH_NO_MINIMUM_RATING: number = 0

export const PROSPECT_SEARCH_MINIMUM_REVIEWS_FOR_RATING: number = 3

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

export const PROSPECT_SEARCH_DEFAULT_VALIDATION_MODE: ProspectSearchValidationMode = 'manual'

export const PROSPECT_SEARCH_VALIDATION_OBJECTIVE_LABELS: Record<ProspectSearchValidationMode, string> = {
  manual: 'vous validez chaque lead',
  automatic: 'les leads complets entrent seuls',
}

export const PROSPECT_SEARCH_VALIDATION_OPTIONS: ProspectSearchValidationOption[] = [
  {
    value: 'manual',
    label: 'Je valide',
    description:
      "L'app propose chaque lead avec ses preuves. Rien n'entre dans vos prospects sans votre accord : vous acceptez ou refusez.",
    icon: 'i-lucide-hand',
  },
  {
    value: 'automatic',
    label: 'Automatique',
    description: 'Les leads complets entrent seuls dans vos prospects. Seuls les cas douteux attendent votre décision.',
    icon: 'i-lucide-bot',
  },
]

export const PROSPECT_SEARCH_LEAD_QUALITY_PRESENTATION: Partial<
  Record<ProspectSearchCandidateStatus, StatusPresentation>
> = {
  kept: { label: 'Complet', badgeClass: 'app-badge--success' },
  set_aside: { label: 'Un seul contact', badgeClass: '' },
  to_confirm: { label: 'À vérifier', badgeClass: 'app-badge--progress' },
}

export const PROSPECT_SEARCH_EMAIL_PROOF_LABELS: Record<ProspectSearchEmailProofLevel, string> = {
  a: 'publié par le pro',
  b: 'donné par un annuaire',
  c: 'sans preuve franche',
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
  'awaiting_decision',
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
  awaiting_decision: 'Déjà proposé, en attente de validation',
  previously_rejected: 'Écarté par une recherche précédente',
  do_not_contact: 'Marqué « ne plus contacter »',
  manual: 'Refusé à la main',
}

export const PROSPECT_SEARCH_UNEXPLAINED_REJECT_LABEL: string = 'Autre raison'

export const PROSPECT_SEARCH_MAXIMUM_DECISIONS_PER_REQUEST: number = 100

export const PROSPECT_SEARCH_TUNNEL_STEPS: ProspectSearchStepDefinition[] = [
  { key: 'target', label: 'Cible', hint: 'Métiers et nombre' },
  { key: 'zone', label: 'Zone', hint: 'Pays et villes' },
  { key: 'criteria', label: 'Critères', hint: 'Contact, site, note, validation' },
  { key: 'launch', label: 'Lancer', hint: 'Vérifier et démarrer' },
]

export const PROSPECT_SEARCH_EMPTY_LEADS_NOTICES: Record<
  ProspectSearchEmptyLeadsSituation,
  ProspectSearchEmptyLeadsNotice
> = {
  noMatchingLead: {
    title: 'Aucun lead ne correspond',
    description: 'Essayez de modifier vos filtres pour élargir la sélection.',
    shouldOfferNewSearch: false,
  },
  searchRunning: {
    title: 'La recherche tourne',
    description:
      "Les leads arrivent ici dès qu'ils sont vérifiés. Vous les acceptez ou les refusez un par un, ou plusieurs à la fois.",
    shouldOfferNewSearch: false,
  },
  nothingToDecide: {
    title: 'Aucun lead à valider',
    description:
      'Lancez une recherche : chaque lead arrive ici avec ses preuves, et vous décidez de ceux qui entrent dans vos prospects.',
    shouldOfferNewSearch: true,
  },
}

export const PROSPECT_SEARCH_WEBSITE_WARNINGS: Record<string, StatusPresentation> = {
  dead: { label: 'site en panne', badgeClass: 'app-badge--danger' },
  placeholder: { label: 'mini-site annuaire', badgeClass: '' },
}

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
