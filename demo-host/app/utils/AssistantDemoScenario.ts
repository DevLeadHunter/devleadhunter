import type { AssistantLeadSummary } from '~/types/AssistantChat'

/** An example request per trade, shown on the business's phone before the visitor sends a real one. */
type TradeExample = {
  /** Words of the trade found in its Google category (folded, lower case). */
  keywords: string[]
  /** What the example customer asks for, as the alert would summarise it. */
  need: string
  /** What kind of request the example is: it sets the label of the alert. */
  kind: AssistantLeadSummary['kind']
  /** Whether the example customer sent a photo. */
  hasPhoto: boolean
  /** The wished moment of an appointment (« samedi matin »), empty when none. */
  slots: string
}

const TRADE_EXAMPLES: TradeExample[] = [
  {
    keywords: ['couvreur', 'toiture', 'charpent', 'zingu'],
    need: 'fuite après la tempête, tuiles déplacées côté rue',
    kind: 'quote',
    hasPhoto: true,
    slots: '',
  },
  {
    keywords: ['plomb', 'chauffag', 'sanitaire'],
    need: "fuite sous l'évier de la cuisine, ça goutte",
    kind: 'quote',
    hasPhoto: true,
    slots: '',
  },
  {
    keywords: ['electric', 'électric'],
    need: 'plus de courant dans la cuisine, le tableau saute',
    kind: 'question',
    hasPhoto: false,
    slots: '',
  },
  {
    keywords: ['carross', 'garage', 'mecani', 'mécani', 'automobile'],
    need: 'rayure sur la portière avant droite, devis carrosserie',
    kind: 'quote',
    hasPhoto: true,
    slots: '',
  },
  {
    keywords: ['paysag', 'jardin', 'espaces verts'],
    need: 'taille de haie sur 30 m et tonte, devis annuel',
    kind: 'quote',
    hasPhoto: false,
    slots: '',
  },
  {
    keywords: ['macon', 'maçon', 'batiment', 'bâtiment', 'renov', 'rénov'],
    need: 'fissure sur le mur du garage, devis reprise',
    kind: 'quote',
    hasPhoto: true,
    slots: '',
  },
  {
    keywords: ['menuis', 'fenetr', 'fenêtr'],
    need: 'fenêtre qui ferme mal, devis remplacement',
    kind: 'quote',
    hasPhoto: true,
    slots: '',
  },
  { keywords: ['peintre', 'peinture'], need: 'salon de 25 m² à repeindre', kind: 'quote', hasPhoto: false, slots: '' },
  { keywords: ['serrur'], need: "porte claquée, clés à l'intérieur", kind: 'question', hasPhoto: false, slots: '' },
  {
    keywords: ['coiff', 'barbier'],
    need: 'coupe et barbe',
    kind: 'appointment',
    hasPhoto: false,
    slots: 'samedi matin',
  },
  {
    keywords: ['restaurant', 'traiteur', 'pizz', 'brasserie'],
    need: 'table pour 6, un menu sans gluten',
    kind: 'appointment',
    hasPhoto: false,
    slots: 'samedi soir',
  },
  {
    keywords: ['dentist', 'ostéo', 'osteo', 'kiné', 'kine'],
    need: 'douleur depuis hier, premier rendez-vous possible',
    kind: 'appointment',
    hasPhoto: false,
    slots: '',
  },
  {
    keywords: ['immobil'],
    need: 'estimation de la maison avant mise en vente',
    kind: 'question',
    hasPhoto: false,
    slots: '',
  },
]

const DEFAULT_EXAMPLE: TradeExample = {
  keywords: [],
  need: 'rappel souhaité en journée',
  kind: 'quote',
  hasPhoto: false,
  slots: '',
}

/** The customer of the example, the same for every trade. */
const EXAMPLE_NAME: string = 'Claire Martin'
const EXAMPLE_CONTACT: string = '06 12 34 56 78'

/**
 * The scene of the demo page: what a customer of this trade asks, and what the business receives.
 */
export class AssistantDemoScenario {
  /**
   * The trade as a customer would type it in Google (« couvreur »), from the Google category.
   * @param tradeLabel - The Google Maps category, or null.
   * @returns The lower-case trade, or « artisan » when unknown.
   */
  static searchWord(tradeLabel: string | null): string {
    const trade: string = (tradeLabel ?? '').trim().toLowerCase()
    return trade || 'artisan'
  }

  /**
   * The example request of the trade, shown on the business's phone until a real one comes in.
   * @param tradeLabel - The Google Maps category, or null.
   * @returns The example, as the alert would summarise it.
   */
  static example(tradeLabel: string | null): AssistantLeadSummary {
    const folded: string = AssistantDemoScenario.fold(tradeLabel ?? '')
    const match: TradeExample =
      TRADE_EXAMPLES.find((example: TradeExample): boolean =>
        example.keywords.some((keyword: string): boolean => folded.includes(AssistantDemoScenario.fold(keyword))),
      ) ?? DEFAULT_EXAMPLE
    return {
      name: EXAMPLE_NAME,
      contact: EXAMPLE_CONTACT,
      need: match.need,
      kind: match.kind,
      slots: match.slots,
      booked: false,
      hasPhoto: match.hasPhoto,
    }
  }

  /**
   * The alert SMS as the business receives it, written like the real one (`AlertSms.new_request` on the API):
   * « Nouvelle demande de devis (photo) de Marc, 06…, pour sam. 27/09 matin : … » or, once booked in the agenda,
   * « RDV réservé le mer. 30/09 à 08:00 par Marc, 06… : … ».
   * @param summary - What the visitor just sent.
   * @returns The text of the SMS.
   */
  static alertText(summary: AssistantLeadSummary): string {
    const need: string = (summary.need.trim() || 'rappel souhaité').replace(/[.!?…]+$/u, '')
    if (summary.booked && summary.slots) {
      return `RDV réservé le ${summary.slots} par ${summary.name}, ${summary.contact} : ${need}.`
    }
    const label: string =
      summary.kind === 'appointment'
        ? 'Nouvelle demande de RDV'
        : summary.kind === 'quote'
          ? 'Nouvelle demande de devis'
          : 'Nouvelle demande'
    const photo: string = summary.hasPhoto ? ' (photo)' : ''
    const slots: string = summary.slots ? `, pour ${summary.slots}` : ''
    return `${label}${photo} de ${summary.name}, ${summary.contact}${slots} : ${need}.`
  }

  /**
   * The example alert shown before any real request, for the trade.
   * @param tradeLabel - The Google Maps category, or null.
   * @returns The text of the example SMS.
   */
  static exampleAlertText(tradeLabel: string | null): string {
    return AssistantDemoScenario.alertText(AssistantDemoScenario.example(tradeLabel))
  }

  /**
   * Lower-case text without accents, to match keywords against a Google category.
   * @param value - The text.
   * @returns The folded text.
   */
  private static fold(value: string): string {
    return value
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
  }
}
