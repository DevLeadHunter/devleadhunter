import type { PublisherContact, PublisherLegalIdentity } from '~/types/Publisher'

export const PUBLISHER_CONTACT: PublisherContact = {
  phoneHref: 'tel:+33642193812',
  email: 'contact@dibodev.fr',
  emailHref: 'mailto:contact@dibodev.fr',
  websiteUrl: 'https://dibodev.fr',
  websiteLabel: 'dibodev.fr',
  portraitSrc: '/images/contact/leo-guillaume.webp',
}

export const PUBLISHER_LEGAL_IDENTITY: PublisherLegalIdentity = {
  fullName: 'Léo Guillaume',
  address: '6 rue Simone Morand, Apt A13, 35230 Saint-Erblon, France',
  siret: '988 307 906 00020',
  vatNumber: 'FR02 988 307 906',
  hostName: 'OVH SAS',
  hostAddress: '2 rue Kellermann, 59100 Roubaix, France',
  hostPhone: '1007',
  hostWebsite: 'ovhcloud.com',
}
