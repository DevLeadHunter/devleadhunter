export type LegalDocumentId = 'notice' | 'privacy' | 'terms'

export type LegalDocumentLink = {
  id: LegalDocumentId
  path: string
  labelKey: string
}

export type LandingLegalDocumentProps = {
  documentId: LegalDocumentId
  titleKey: string
  introKey: string
}
