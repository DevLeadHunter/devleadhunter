export type SchemaOrgBusinessType =
  | 'LocalBusiness'
  | 'HomeAndConstructionBusiness'
  | 'Plumber'
  | 'Electrician'
  | 'RoofingContractor'
  | 'HousePainter'
  | 'Locksmith'
  | 'MovingCompany'
  | 'HVACBusiness'
  | 'GeneralContractor'
  | 'AutomotiveBusiness'
  | 'AutoRepair'
  | 'AutoBodyShop'
  | 'AutoDealer'
  | 'AutoWash'
  | 'TireShop'
  | 'HairSalon'
  | 'BeautySalon'
  | 'NailSalon'
  | 'Dentist'
  | 'FoodEstablishment'
  | 'Restaurant'
  | 'Bakery'
  | 'CafeOrCoffeeShop'
  | 'Florist'

export type SchemaOrgTradeRule = {
  keywords: string[]
  type: SchemaOrgBusinessType
}

export type SchemaOrgDayOfWeek = 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday' | 'Sunday'

export type SchemaOrgPostalAddress = {
  '@type': 'PostalAddress'
  streetAddress?: string
  postalCode?: string
  addressLocality?: string
  addressRegion?: string
  addressCountry?: string
}

/** What a listing's one-line address says, each part empty when the line does not tell it. */
export type PostalAddressParts = {
  street: string
  postalCode: string
  locality: string
  region: string
}

export type SchemaOrgOpeningHoursSpecification = {
  '@type': 'OpeningHoursSpecification'
  dayOfWeek: SchemaOrgDayOfWeek[]
  opens: string
  closes: string
}

/** Times in 24-hour `HH:MM`. */
export type OpeningTimeRange = {
  opens: string
  closes: string
}

export type OpeningRangeDays = {
  range: OpeningTimeRange
  days: Set<SchemaOrgDayOfWeek>
}

export type SchemaOrgGeoCoordinates = {
  '@type': 'GeoCoordinates'
  latitude: number
  longitude: number
}

export type SchemaOrgAggregateRating = {
  '@type': 'AggregateRating'
  ratingValue: number
  reviewCount: number
  bestRating: number
  worstRating: number
}

export type SchemaOrgGovernmentOrganization = {
  '@type': 'GovernmentOrganization'
  name: string
  url: string
}

export type SchemaOrgLicenseCredential = {
  '@type': 'EducationalOccupationalCredential'
  credentialCategory: 'license'
  name: string
  identifier: string
  recognizedBy?: SchemaOrgGovernmentOrganization
}

export type SchemaOrgLocalBusiness = {
  '@context': 'https://schema.org'
  '@type': SchemaOrgBusinessType
  '@id': string
  name: string
  url: string
  telephone?: string
  email?: string
  address?: SchemaOrgPostalAddress
  geo?: SchemaOrgGeoCoordinates
  openingHoursSpecification?: SchemaOrgOpeningHoursSpecification[]
  aggregateRating?: SchemaOrgAggregateRating
  image?: string
  logo?: string
  areaServed?: string | string[]
  sameAs?: string[]
  hasCredential?: SchemaOrgLicenseCredential
}
