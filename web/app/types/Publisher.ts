/** The phone number lives in i18n (`publisher.phone`): its display format depends on the language. */
export type PublisherContact = {
  phoneHref: string
  email: string
  emailHref: string
  websiteUrl: string
  websiteLabel: string
  portraitSrc: string
}

export type PublisherLegalIdentity = {
  fullName: string
  address: string
  siret: string
  vatNumber: string
  hostName: string
  hostAddress: string
  hostPhone: string
  hostWebsite: string
}
