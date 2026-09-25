import type { AssistantLeadSummary } from '~/types/AssistantChat'

/** An example request per trade, shown on the business's phone before the visitor sends a real one. */
type TradeExample = {
  /** Words of the trade found in its Google category (folded, lower case). */
  keywords: string[]
  /** What the example customer asks for, as the alert would summarise it. */
  need: string
}

const TRADE_EXAMPLES: TradeExample[] = [
  { keywords: ['couvreur', 'toiture', 'charpent', 'zingu'], need: 'fuite après la tempête, tuiles déplacées côté rue' },
  { keywords: ['plomb', 'chauffag', 'sanitaire'], need: "fuite sous l'évier de la cuisine, ça goutte" },
  { keywords: ['electric', 'électric'], need: 'plus de courant dans la cuisine, le tableau saute' },
  {
    keywords: ['carross', 'garage', 'mecani', 'mécani', 'auto'],
    need: 'rayure sur la portière avant droite, devis carrosserie',
  },
  { keywords: ['paysag', 'jardin', 'espaces verts'], need: 'taille de haie sur 30 m et tonte, devis annuel' },
  {
    keywords: ['macon', 'maçon', 'batiment', 'bâtiment', 'renov', 'rénov'],
    need: 'fissure sur le mur du garage, devis reprise',
  },
  { keywords: ['menuis', 'fenetr', 'fenêtr'], need: 'fenêtre qui ferme mal, devis remplacement' },
  { keywords: ['peintre', 'peinture'], need: 'salon de 25 m² à repeindre, devis' },
  { keywords: ['serrur'], need: 'porte claquée, clés à l’intérieur' },
  { keywords: ['coiff', 'barbier', 'salon'], need: 'coupe et barbe samedi matin, rendez-vous' },
  { keywords: ['restaurant', 'traiteur', 'pizz', 'brasserie'], need: 'table pour 6 samedi soir, un menu sans gluten' },
  {
    keywords: ['dentist', 'cabinet', 'ostéo', 'osteo', 'kiné', 'kine'],
    need: 'douleur depuis hier, premier rendez-vous possible',
  },
  { keywords: ['immobil', 'agence'], need: 'estimation de la maison avant mise en vente' },
]

const DEFAULT_NEED: string = 'demande de devis, rappel souhaité en journée'

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
   * An example request for the trade, shown on the business's phone until a real one comes in.
   * @param tradeLabel - The Google Maps category, or null.
   * @returns The example need, as the alert summarises it.
   */
  static exampleNeed(tradeLabel: string | null): string {
    const folded: string = (tradeLabel ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    const match: TradeExample | undefined = TRADE_EXAMPLES.find((example: TradeExample): boolean =>
      example.keywords.some((keyword: string): boolean =>
        folded.includes(keyword.normalize('NFD').replace(/[̀-ͯ]/g, '')),
      ),
    )
    return match?.need ?? DEFAULT_NEED
  }

  /**
   * The alert SMS as the business receives it, written like the real one (label, name, contact, summary).
   * @param summary - What the visitor just sent.
   * @returns The text of the SMS.
   */
  static alertText(summary: AssistantLeadSummary): string {
    const label: string =
      summary.kind === 'appointment'
        ? 'Nouvelle demande de RDV'
        : summary.kind === 'quote'
          ? 'Nouvelle demande de devis'
          : 'Nouvelle demande'
    const need: string = summary.need || 'rappel souhaité'
    const slots: string = summary.slots ? `, pour ${summary.slots}` : ''
    const photo: string = summary.hasPhoto ? ' Photo jointe.' : ''
    return `${label} de ${summary.name}, ${summary.contact}${slots} : ${need}.${photo}`
  }

  /**
   * The example alert shown before any real request, for the trade.
   * @param tradeLabel - The Google Maps category, or null.
   * @returns The text of the example SMS.
   */
  static exampleAlertText(tradeLabel: string | null): string {
    return `Nouvelle demande de devis de Claire Martin, 06 12 34 56 78 : ${AssistantDemoScenario.exampleNeed(tradeLabel)}. Photo jointe.`
  }
}
