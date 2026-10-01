export type SiteContactTopic = 'discover' | 'credits' | 'account' | 'privacy' | 'other'

/** `website` is a honeypot: the field is hidden from people, so only bots fill it. */
export type SiteContactPayload = {
  topic: SiteContactTopic
  name: string
  email: string
  phone: string | null
  message: string
  locale: string
  website: string
}

export type SiteContactResponse = {
  status: 'sent'
}
