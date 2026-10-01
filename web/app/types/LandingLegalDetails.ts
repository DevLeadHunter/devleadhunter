export type LegalDetailRow = {
  label: string
  value: string
  note?: string
}

export type LandingLegalDetailsProps = {
  rows: LegalDetailRow[]
}
