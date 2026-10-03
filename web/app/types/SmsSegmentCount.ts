export type SmsSegmentCountPayload = {
  text: string
  prospect_id: number | null
}

/** What a typed message bills once smsmode appends the opt-out mention of its recipient's country. */
export type SmsSegmentCount = {
  characters: number
  segments: number
  maximum_segments: number
  is_unicode: boolean
}
