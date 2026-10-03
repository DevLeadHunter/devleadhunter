import type { Prospect, ProspectCountry } from '~/types'
import type { EnrichmentOpeningHours, EnrichmentReview, ImportedEnrichmentPayload } from '~/services/enrichmentService'
import type { ProspectCountryOption } from '~/utils/prospectCountries'
import { ProspectCountries } from '~/utils/prospectCountries'

/** JSON import/export helpers for prospects (client-side exchange format). */

/** Shape of one prospect inside an import/export JSON file. */
export type ProspectJsonItem = {
  name: string
  address?: string
  city?: string
  country?: ProspectCountry
  phone?: string
  email?: string
  website?: string
  category?: string
  confidence?: number
  google_maps_url?: string
  facebook_url?: string
  contact_first_name?: string
  contact_last_name?: string
  enrichment?: ImportedEnrichmentPayload
}

/** Result of parsing an import file: valid rows + human-readable row errors. */
export type ProspectJsonParseResult = {
  valid: ProspectJsonItem[]
  errors: string[]
}

/**
 * Trigger a browser download of the given content as a file.
 * @param filename - Suggested file name.
 * @param content - Text content of the file.
 */
function downloadFile(filename: string, content: string): void {
  const blob: Blob = new Blob([content], { type: 'application/json;charset=utf-8' })
  const url: string = URL.createObjectURL(blob)
  const anchor: HTMLAnchorElement = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

/**
 * Download the selected prospects as a JSON file (import-compatible shape).
 * The rich enrichment block is not re-exported — the exported list carries the
 * prospect fields only, enough to re-import and re-enrich.
 * @param prospects - Prospects to export.
 */
export function downloadProspectsJson(prospects: Prospect[]): void {
  const items: ProspectJsonItem[] = prospects.map((prospect: Prospect): ProspectJsonItem => {
    return {
      name: prospect.name,
      address: prospect.address ?? '',
      city: prospect.city ?? '',
      country: prospect.country ?? ProspectCountries.france.code,
      phone: prospect.phone ?? '',
      email: prospect.email ?? '',
      website: prospect.website ?? '',
      google_maps_url: prospect.google_maps_url ?? '',
      facebook_url: prospect.facebook_url ?? '',
      category: prospect.category,
      confidence: prospect.confidence,
    }
  })
  const date: string = new Date().toISOString().slice(0, 10)
  downloadFile(`prospects-${date}.json`, JSON.stringify(items, null, 2))
}

/**
 * Download a documented JSON template for manual prospect imports. The first row
 * is a fully-enriched example (import-ready to generate a site); the second is a
 * minimal row showing that everything past `name` is optional.
 */
export function downloadProspectTemplateJson(): void {
  const template: ProspectJsonItem[] = [
    {
      name: 'Plomberie Dupont (exemple — remplacez et dupliquez cette ligne)',
      address: '12 rue des Artisans',
      city: 'Lyon',
      country: 'FR',
      phone: '04 72 00 00 00',
      email: 'contact@plomberie-dupont.fr',
      website: '',
      category: 'plombier',
      confidence: 4,
      google_maps_url: 'https://www.google.com/maps/place/...',
      facebook_url: 'https://www.facebook.com/votre-page',
      contact_first_name: 'Jean',
      contact_last_name: 'Dupont',
      enrichment: {
        logo_url: 'https://exemple.fr/logo.png',
        rating: 4.8,
        reviews_count: 127,
        description: 'Artisan plombier à Lyon depuis 2008 : dépannage, rénovation, chauffe-eau.',
        photos: ['https://exemple.fr/photo-1.jpg', 'https://exemple.fr/photo-2.jpg'],
        reviews: [{ author: 'Marie L.', rating: 5, text: 'Intervention rapide et soignée.' }],
        opening_hours: [
          { day: 'Lundi', hours: '08:00 – 18:00' },
          { day: 'Samedi', hours: 'Fermé' },
        ],
        services: ['Dépannage', 'Rénovation salle de bain', 'Installation chauffe-eau'],
        social_links: { facebook: 'https://facebook.com/...', instagram: 'https://instagram.com/...' },
        place_city: 'Lyon',
        place_postal_code: '69003',
      },
    },
    {
      name: '',
      address: '',
      city: '',
      phone: '',
      email: '',
      website: '',
      category: '',
    },
  ]
  downloadFile('modele-prospects.json', JSON.stringify(template, null, 2))
}

/**
 * Return the value as a trimmed string ('' when absent or not a string).
 * @param value - Raw JSON value.
 * @returns Trimmed string.
 */
function cleanString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

/**
 * Return a trimmed non-empty string, or undefined when absent/blank.
 * @param value - Raw JSON value.
 * @returns The string, or undefined.
 */
function optionalString(value: unknown): string | undefined {
  const text: string = cleanString(value)
  return text === '' ? undefined : text
}

/**
 * Read the country of an imported row: a supported ISO code in any case, France when absent or unknown.
 * @param value - Raw JSON value.
 * @returns A supported country code.
 */
function importedCountry(value: unknown): ProspectCountry {
  const code: string = cleanString(value).toUpperCase()
  const known: ProspectCountryOption | undefined = ProspectCountries.catalog.find(
    (option: ProspectCountryOption): boolean => option.code === code,
  )
  return known?.code ?? ProspectCountries.france.code
}

/**
 * Return a finite number, or undefined when absent/not numeric.
 * @param value - Raw JSON value.
 * @returns The number, or undefined.
 */
function optionalNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

/**
 * Return an integer confidence score bounded to 1-4, or undefined when absent/out of range.
 * @param value - Raw JSON value.
 * @returns The clamped score, or undefined.
 */
function optionalConfidence(value: unknown): number | undefined {
  const score: number | undefined = optionalNumber(value)
  if (score === undefined) return undefined
  const rounded: number = Math.round(score)
  return rounded >= 1 && rounded <= 4 ? rounded : undefined
}

/**
 * Return the array's non-empty trimmed strings, or undefined when none.
 * @param value - Raw JSON value.
 * @returns The cleaned string list, or undefined.
 */
function optionalStringArray(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined
  const items: string[] = value
    .map((entry: unknown): string => cleanString(entry))
    .filter((entry: string): boolean => entry !== '')
  return items.length > 0 ? items : undefined
}

/**
 * Parse the reviews array into {author, text, rating} rows.
 * @param value - Raw JSON value.
 * @returns The usable reviews, or undefined when none.
 */
function optionalReviews(value: unknown): EnrichmentReview[] | undefined {
  if (!Array.isArray(value)) return undefined
  const reviews: EnrichmentReview[] = []
  value.forEach((entry: unknown): void => {
    if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) return
    const record: Record<string, unknown> = entry as Record<string, unknown>
    const author: string | undefined = optionalString(record.author)
    const text: string | undefined = optionalString(record.text)
    const rating: number | undefined = optionalNumber(record.rating)
    if (author === undefined && text === undefined && rating === undefined) return
    const review: EnrichmentReview = {}
    if (author !== undefined) review.author = author
    if (text !== undefined) review.text = text
    if (rating !== undefined) review.rating = rating
    reviews.push(review)
  })
  return reviews.length > 0 ? reviews : undefined
}

/**
 * Parse the opening-hours array into {day, hours} rows.
 * @param value - Raw JSON value.
 * @returns The usable rows, or undefined when none.
 */
function optionalOpeningHours(value: unknown): EnrichmentOpeningHours[] | undefined {
  if (!Array.isArray(value)) return undefined
  const rows: EnrichmentOpeningHours[] = []
  value.forEach((entry: unknown): void => {
    if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) return
    const record: Record<string, unknown> = entry as Record<string, unknown>
    const day: string | undefined = optionalString(record.day)
    const hours: string | undefined = optionalString(record.hours)
    if (day === undefined && hours === undefined) return
    const row: EnrichmentOpeningHours = {}
    if (day !== undefined) row.day = day
    if (hours !== undefined) row.hours = hours
    rows.push(row)
  })
  return rows.length > 0 ? rows : undefined
}

/**
 * Parse the social-links object into a { network: url } map.
 * @param value - Raw JSON value.
 * @returns The links map, or undefined when empty.
 */
function optionalSocialLinks(value: unknown): Record<string, string> | undefined {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return undefined
  const links: Record<string, string> = {}
  for (const [network, url] of Object.entries(value as Record<string, unknown>)) {
    const cleaned: string = cleanString(url)
    if (cleaned !== '') links[network] = cleaned
  }
  return Object.keys(links).length > 0 ? links : undefined
}

/**
 * Parse the optional enrichment block of an import row. Returns undefined when
 * the block is absent or holds nothing usable, so a bare prospect stays bare and
 * no empty enrichment is posted.
 * @param value - Raw JSON value of the `enrichment` key.
 * @returns The cleaned enrichment payload, or undefined.
 */
function parseEnrichment(value: unknown): ImportedEnrichmentPayload | undefined {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return undefined
  const record: Record<string, unknown> = value as Record<string, unknown>
  const enrichment: ImportedEnrichmentPayload = {}

  const logoUrl: string | undefined = optionalString(record.logo_url)
  if (logoUrl !== undefined) enrichment.logo_url = logoUrl
  const rating: number | undefined = optionalNumber(record.rating)
  if (rating !== undefined) enrichment.rating = rating
  const reviewsCount: number | undefined = optionalNumber(record.reviews_count)
  if (reviewsCount !== undefined) enrichment.reviews_count = reviewsCount
  const description: string | undefined = optionalString(record.description)
  if (description !== undefined) enrichment.description = description
  const photos: string[] | undefined = optionalStringArray(record.photos)
  if (photos !== undefined) enrichment.photos = photos
  const reviews: EnrichmentReview[] | undefined = optionalReviews(record.reviews)
  if (reviews !== undefined) enrichment.reviews = reviews
  const openingHours: EnrichmentOpeningHours[] | undefined = optionalOpeningHours(record.opening_hours)
  if (openingHours !== undefined) enrichment.opening_hours = openingHours
  const services: string[] | undefined = optionalStringArray(record.services)
  if (services !== undefined) enrichment.services = services
  const socialLinks: Record<string, string> | undefined = optionalSocialLinks(record.social_links)
  if (socialLinks !== undefined) enrichment.social_links = socialLinks
  const placeTitle: string | undefined = optionalString(record.place_title)
  if (placeTitle !== undefined) enrichment.place_title = placeTitle
  const placeCity: string | undefined = optionalString(record.place_city)
  if (placeCity !== undefined) enrichment.place_city = placeCity
  const placePostalCode: string | undefined = optionalString(record.place_postal_code)
  if (placePostalCode !== undefined) enrichment.place_postal_code = placePostalCode

  return Object.keys(enrichment).length > 0 ? enrichment : undefined
}

/**
 * Parse and validate the content of an import JSON file.
 * Accepted shape: an array of objects with at least a non-empty `name`
 * (`category` falls back to « Entreprise » when missing). Rows failing
 * validation are reported, valid rows are returned normalised. The optional
 * `google_maps_url` and `enrichment` block are parsed leniently — a malformed
 * enrichment is dropped, never a reason to reject the prospect.
 * @param text - Raw file content.
 * @returns Valid items + per-row error messages.
 * @throws When the file is not valid JSON or not an array.
 */
export function parseProspectsJson(text: string): ProspectJsonParseResult {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    throw new Error('Fichier invalide — ce n’est pas du JSON.')
  }
  if (!Array.isArray(raw)) {
    throw new Error('Le JSON doit être un tableau de prospects (utilisez le modèle).')
  }

  const valid: ProspectJsonItem[] = []
  const errors: string[] = []

  raw.forEach((entry: unknown, index: number): void => {
    if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) {
      errors.push(`Ligne ${index + 1} : entrée ignorée (objet attendu).`)
      return
    }
    const record: Record<string, unknown> = entry as Record<string, unknown>
    const name: string = cleanString(record.name)
    if (!name || name.startsWith('Plomberie Dupont (exemple')) {
      // Empty rows and the untouched template example are silently skipped.
      if (Object.values(record).some((value: unknown): boolean => cleanString(value) !== '')) {
        errors.push(`Ligne ${index + 1} : « name » est requis — entrée ignorée.`)
      }
      return
    }
    const item: ProspectJsonItem = {
      name,
      address: cleanString(record.address),
      city: cleanString(record.city),
      country: importedCountry(record.country),
      phone: cleanString(record.phone),
      email: cleanString(record.email),
      website: cleanString(record.website),
      category: cleanString(record.category) || 'Entreprise',
    }
    const confidence: number | undefined = optionalConfidence(record.confidence)
    if (confidence !== undefined) item.confidence = confidence
    const googleMapsUrl: string | undefined = optionalString(record.google_maps_url)
    if (googleMapsUrl !== undefined) item.google_maps_url = googleMapsUrl
    const facebookUrl: string | undefined = optionalString(record.facebook_url)
    if (facebookUrl !== undefined) item.facebook_url = facebookUrl
    const contactFirstName: string | undefined = optionalString(record.contact_first_name)
    if (contactFirstName !== undefined) item.contact_first_name = contactFirstName
    const contactLastName: string | undefined = optionalString(record.contact_last_name)
    if (contactLastName !== undefined) item.contact_last_name = contactLastName
    const enrichment: ImportedEnrichmentPayload | undefined = parseEnrichment(record.enrichment)
    if (enrichment !== undefined) item.enrichment = enrichment
    valid.push(item)
  })

  return { valid, errors }
}
