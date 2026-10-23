import type { DemoSiteTaxCredit } from '~/services/demoSiteService'
import type { TaxCreditDraft } from '~/types/TaxCreditEditor'

/** Texts proposed when the section is switched on from nothing: a garden-maintenance provider registered « services à la personne ». */
const PROPOSED_TEXTS: TaxCreditDraft = {
  isSectionShown: true,
  heading: 'Votre entretien de jardin à moitié prix',
  lead: "Je suis déclaré services à la personne : la moitié de ce que vous me payez pour l'entretien de votre jardin vous revient en crédit d'impôt, que vous soyez imposable ou non.",
  points: [
    '50 % de la facture remboursés, même sans impôt à payer',
    "Jusqu'à 5 000 € de travaux par an, soit 2 500 € de crédit d'impôt",
    'Tonte, taille de haies, désherbage, débroussaillage, ramassage des feuilles',
    'Une attestation fiscale remise chaque année pour votre déclaration',
  ],
  note: 'Plafond de 5 000 € de dépenses par an et par foyer fiscal.',
  faqQuestion: "Puis-je bénéficier du crédit d'impôt de 50 % ?",
  faqAnswer:
    "Oui. Je suis déclaré services à la personne : l'entretien courant de votre jardin (tonte, taille, désherbage, débroussaillage, ramassage des feuilles) ouvre droit à un crédit d'impôt de 50 % de la somme payée, dans la limite de 5 000 € de dépenses par an et par foyer. Je vous remets chaque année l'attestation fiscale à joindre à votre déclaration.",
}

/**
 * Conversions between the « crédit d'impôt » section of the API and the editor draft.
 */
export class TaxCreditSection {
  /** Key points the section shows at most (the API drops the rest). */
  static readonly MAX_POINTS: number = 6

  /**
   * The editor draft of a published section.
   * @param taxCredit - The section the API returned, null when the site has none.
   * @returns A shown draft carrying the section's texts, or a hidden, blank one.
   */
  static toDraft(taxCredit: DemoSiteTaxCredit | null | undefined): TaxCreditDraft {
    if (!taxCredit) {
      return {
        isSectionShown: false,
        heading: '',
        lead: '',
        points: [],
        note: '',
        faqQuestion: '',
        faqAnswer: '',
      }
    }
    return {
      isSectionShown: true,
      heading: taxCredit.heading,
      lead: taxCredit.lead,
      points: [...taxCredit.points],
      note: taxCredit.note,
      faqQuestion: taxCredit.faq_question,
      faqAnswer: taxCredit.faq_answer,
    }
  }

  /**
   * A shown draft filled with the proposed texts, for a section switched on from nothing.
   * @returns The draft to edit before publishing.
   */
  static proposedDraft(): TaxCreditDraft {
    return { ...PROPOSED_TEXTS, points: [...PROPOSED_TEXTS.points] }
  }

  /**
   * Whether the draft carries no text at all (nothing worth keeping when the section is switched on).
   * @param draft - The editor draft.
   * @returns True when every text and every point is empty.
   */
  static isBlank(draft: TaxCreditDraft): boolean {
    const texts: string[] = [draft.heading, draft.lead, draft.note, draft.faqQuestion, draft.faqAnswer, ...draft.points]
    return texts.every((text: string): boolean => text.trim().length === 0)
  }

  /**
   * The API payload of the draft (trimmed, empty points dropped); a hidden section is an empty heading, which removes it.
   * @param draft - The editor draft.
   * @returns The section ready for the PATCH.
   */
  static toPayload(draft: TaxCreditDraft): DemoSiteTaxCredit {
    if (!draft.isSectionShown) {
      return { heading: '', lead: '', points: [], note: '', faq_question: '', faq_answer: '' }
    }
    const points: string[] = draft.points
      .map((point: string): string => point.trim())
      .filter((point: string): boolean => point.length > 0)
      .slice(0, TaxCreditSection.MAX_POINTS)
    return {
      heading: draft.heading.trim(),
      lead: draft.lead.trim(),
      points,
      note: draft.note.trim(),
      faq_question: draft.faqQuestion.trim(),
      faq_answer: draft.faqAnswer.trim(),
    }
  }

  /**
   * Signature of what the draft would publish, to detect a pending edit against the published section.
   * @param draft - The editor draft.
   * @returns A string equal for two drafts publishing the same section.
   */
  static signature(draft: TaxCreditDraft): string {
    return JSON.stringify(TaxCreditSection.toPayload(draft))
  }
}
