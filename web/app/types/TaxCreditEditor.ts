/** `isSectionShown` false publishes an empty heading (the section and its FAQ entry leave the site) but keeps the texts for a later switch-on. */
export type TaxCreditDraft = {
  isSectionShown: boolean
  heading: string
  lead: string
  points: string[]
  note: string
  faqQuestion: string
  faqAnswer: string
}

/** The free texts of the draft (everything but the switch and the key points). */
export type TaxCreditDraftTextField = 'heading' | 'lead' | 'note' | 'faqQuestion' | 'faqAnswer'

/** `draft` = the candidate section, owned by the parent (controlled). */
export type TaxCreditEditorProps = {
  draft: TaxCreditDraft
}

export type TaxCreditEditorEmits = {
  'update:draft': [draft: TaxCreditDraft]
}
