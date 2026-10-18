import type { SiteContentOpeningHours, SiteContentSocialLink } from '@devleadhunter/website-content'
import { professionalLicenseLine } from '@devleadhunter/website-content'
import type { DemoSitePublic } from '~/types/demoSite'
import type {
  SchemaOrgAggregateRating,
  SchemaOrgGeoCoordinates,
  SchemaOrgGovernmentOrganization,
  SchemaOrgLicenseCredential,
  SchemaOrgLocalBusiness,
  SchemaOrgOpeningHoursSpecification,
  SchemaOrgPostalAddress,
} from '~/types/SiteStructuredData'
import { SchemaOrgBusinessTypeUtils } from '~/utils/SchemaOrgBusinessTypeUtils'
import { SchemaOrgOpeningHoursUtils } from '~/utils/SchemaOrgOpeningHoursUtils'
import { SchemaOrgPostalAddressUtils } from '~/utils/SchemaOrgPostalAddressUtils'

const EUROPEAN_CALLING_CODE_BY_COUNTRY: Record<string, string> = { FR: '33', BE: '32', CH: '41' }
const NORTH_AMERICAN_CALLING_CODE: string = '1'
const NORTH_AMERICAN_NUMBER_LENGTH: number = 10
const SHORTEST_NATIONAL_NUMBER_LENGTH: number = 9
const LONGEST_NATIONAL_NUMBER_LENGTH: number = 10
const TRUNK_PREFIX: string = '0'
const INTERNATIONAL_PREFIX: string = '00'
const EMAIL: RegExp = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const HTTP_URL: RegExp = /^https?:\/\/\S+$/i
const MAXIMUM_RATING: number = 5
const MINIMUM_RATING: number = 1
const MAXIMUM_LATITUDE: number = 90
const MAXIMUM_LONGITUDE: number = 180
const RBQ_LICENSE: RegExp = /\bRBQ\b/i
const RBQ: SchemaOrgGovernmentOrganization = {
  '@type': 'GovernmentOrganization',
  name: 'Régie du bâtiment du Québec',
  url: 'https://www.rbq.gouv.qc.ca',
}

/**
 * The schema.org description of a site's business, from its content only: a field the content lacks is left out.
 */
export class SiteStructuredDataUtils {
  /**
   * The business behind a site, as Google and AI assistants read it.
   * @param site - The public payload of a demo or a sold site.
   * @param homeUrl - The address of the site's home page.
   * @returns The LocalBusiness (or the trade's own type), null when the site has no name.
   */
  static buildLocalBusiness(site: DemoSitePublic, homeUrl: string): SchemaOrgLocalBusiness | null {
    const content: Record<string, unknown> = site.content_json ?? {}
    const name: string = SiteStructuredDataUtils.readText(content.businessName) || site.business_name.trim()
    if (!name) return null

    const country: string = SiteStructuredDataUtils.readText(content.country).toUpperCase()
    const business: SchemaOrgLocalBusiness = {
      '@context': 'https://schema.org',
      '@type': SchemaOrgBusinessTypeUtils.resolveBusinessType(site.business_category, site.template_id),
      '@id': `${homeUrl}#business`,
      name,
      url: homeUrl,
    }

    const telephone: string = SiteStructuredDataUtils.formatInternationalPhone(
      SiteStructuredDataUtils.readText(content.phone),
      country,
    )
    if (telephone) business.telephone = telephone

    const email: string = SiteStructuredDataUtils.readText(content.email)
    if (EMAIL.test(email)) business.email = email

    const address: SchemaOrgPostalAddress | null = SchemaOrgPostalAddressUtils.buildPostalAddress(
      SiteStructuredDataUtils.readText(content.address),
      SiteStructuredDataUtils.readText(content.city),
      country,
    )
    if (address) business.address = address

    const geo: SchemaOrgGeoCoordinates | null = SiteStructuredDataUtils.buildGeoCoordinates(content.lat, content.lng)
    if (geo) business.geo = geo

    const openingHoursSpecification: SchemaOrgOpeningHoursSpecification[] =
      SchemaOrgOpeningHoursUtils.buildSpecifications(SiteStructuredDataUtils.readOpeningHoursRows(content.openingHours))
    if (openingHoursSpecification.length) business.openingHoursSpecification = openingHoursSpecification

    const aggregateRating: SchemaOrgAggregateRating | null = SiteStructuredDataUtils.buildAggregateRating(
      content.rating,
      content.reviewsCount,
    )
    if (aggregateRating) business.aggregateRating = aggregateRating

    const businessPhoto: string = SiteStructuredDataUtils.readHttpUrl(site.business_photo_url)
    const logo: string = SiteStructuredDataUtils.readHttpUrl(content.logo)
    if (businessPhoto || logo) business.image = businessPhoto || logo
    if (logo) business.logo = logo

    const areaServed: string | string[] | null = SiteStructuredDataUtils.readAreaServed(content.zones, content.area)
    if (areaServed) business.areaServed = areaServed

    const sameAs: string[] = SiteStructuredDataUtils.readProfileUrls(content.social)
    if (sameAs.length) business.sameAs = sameAs

    const license: SchemaOrgLicenseCredential | null = SiteStructuredDataUtils.buildLicenseCredential(
      SiteStructuredDataUtils.readText(content.professionalLicenseLabel),
      SiteStructuredDataUtils.readText(content.professionalLicenseNumber),
    )
    if (license) business.hasCredential = license

    return business
  }

  /**
   * A number written the international way (« 05 65 22 01 82 » in France is « +33565220182 »).
   * @param phone - The number as the site shows it.
   * @param country - The business's ISO country code.
   * @returns The international number; the number as shown when its country's form is unknown; empty when none.
   */
  private static formatInternationalPhone(phone: string, country: string): string {
    const digits: string = phone.replace(/\D/g, '')
    if (!digits) return ''
    if (phone.trim().startsWith('+')) return `+${digits}`
    if (digits.startsWith(INTERNATIONAL_PREFIX)) return `+${digits.slice(INTERNATIONAL_PREFIX.length)}`
    if (country === 'CA' && digits.length === NORTH_AMERICAN_NUMBER_LENGTH) {
      return `+${NORTH_AMERICAN_CALLING_CODE}${digits}`
    }

    const callingCode: string | undefined = EUROPEAN_CALLING_CODE_BY_COUNTRY[country]
    const isNationalNumber: boolean =
      digits.startsWith(TRUNK_PREFIX) &&
      digits.length >= SHORTEST_NATIONAL_NUMBER_LENGTH &&
      digits.length <= LONGEST_NATIONAL_NUMBER_LENGTH
    if (callingCode && isNationalNumber) return `+${callingCode}${digits.slice(TRUNK_PREFIX.length)}`
    return phone.trim()
  }

  /**
   * The content's opening hours rows, whatever the content holds there.
   * @param openingHours - The content's `openingHours`.
   * @returns Its rows that are objects.
   */
  private static readOpeningHoursRows(openingHours: unknown): SiteContentOpeningHours[] {
    if (!Array.isArray(openingHours)) return []
    return openingHours.filter(
      (row: unknown): row is SiteContentOpeningHours => typeof row === 'object' && row !== null,
    )
  }

  /**
   * The business's position, when the listing gave one.
   * @param latitude - The content's latitude.
   * @param longitude - The content's longitude.
   * @returns The coordinates, null when either is missing or out of range.
   */
  private static buildGeoCoordinates(latitude: unknown, longitude: unknown): SchemaOrgGeoCoordinates | null {
    const latitudeValue: number | null = SiteStructuredDataUtils.readNumber(latitude)
    const longitudeValue: number | null = SiteStructuredDataUtils.readNumber(longitude)
    if (latitudeValue === null || longitudeValue === null) return null
    if (Math.abs(latitudeValue) > MAXIMUM_LATITUDE || Math.abs(longitudeValue) > MAXIMUM_LONGITUDE) return null

    return { '@type': 'GeoCoordinates', latitude: latitudeValue, longitude: longitudeValue }
  }

  /**
   * The listing's real rating and number of reviews.
   * @param rating - The content's rating out of 5.
   * @param reviewsCount - The content's number of reviews.
   * @returns The aggregate rating, null unless both are real.
   */
  private static buildAggregateRating(rating: unknown, reviewsCount: unknown): SchemaOrgAggregateRating | null {
    const ratingValue: number | null = SiteStructuredDataUtils.readNumber(rating)
    const reviewCount: number | null = SiteStructuredDataUtils.readNumber(reviewsCount)
    if (ratingValue === null || reviewCount === null) return null
    if (ratingValue < MINIMUM_RATING || ratingValue > MAXIMUM_RATING) return null
    if (!Number.isInteger(reviewCount) || reviewCount < 1) return null

    return {
      '@type': 'AggregateRating',
      ratingValue,
      reviewCount,
      bestRating: MAXIMUM_RATING,
      worstRating: MINIMUM_RATING,
    }
  }

  /**
   * Where the business works: the towns the site lists, else the area it names.
   * @param zones - The content's towns.
   * @param area - The content's area (« Limoges et ses alentours »).
   * @returns The towns, the area, or null when the site names neither.
   */
  private static readAreaServed(zones: unknown, area: unknown): string | string[] | null {
    const towns: string[] = Array.isArray(zones)
      ? zones.map((zone: unknown): string => SiteStructuredDataUtils.readText(zone)).filter(Boolean)
      : []
    if (towns.length) return towns
    return SiteStructuredDataUtils.readText(area) || null
  }

  /**
   * The business's own pages on social networks.
   * @param social - The content's social links.
   * @returns Their addresses, without duplicates.
   */
  private static readProfileUrls(social: unknown): string[] {
    if (!Array.isArray(social)) return []
    const urls: string[] = social
      .filter((link: unknown): link is SiteContentSocialLink => typeof link === 'object' && link !== null)
      .map((link: SiteContentSocialLink): string => SiteStructuredDataUtils.readHttpUrl(link.url))
      .filter(Boolean)
    return [...new Set(urls)]
  }

  /**
   * The professional licence the site shows (« Licence RBQ 5678-1234-01 »), the RBQ named as its issuer.
   * @param label - The licence's label.
   * @param licenseNumber - The licence's number.
   * @returns The credential, null without a number.
   */
  private static buildLicenseCredential(label: string, licenseNumber: string): SchemaOrgLicenseCredential | null {
    if (!licenseNumber) return null

    const credential: SchemaOrgLicenseCredential = {
      '@type': 'EducationalOccupationalCredential',
      credentialCategory: 'license',
      name: professionalLicenseLine({ professionalLicenseLabel: label, professionalLicenseNumber: licenseNumber }),
      identifier: licenseNumber,
    }
    if (RBQ_LICENSE.test(label)) credential.recognizedBy = RBQ
    return credential
  }

  /**
   * A content value as trimmed text.
   * @param value - The value.
   * @returns The text, empty when the value is not a string.
   */
  private static readText(value: unknown): string {
    return typeof value === 'string' ? value.trim() : ''
  }

  /**
   * A content value as a number, Storyblok writing numbers as text.
   * @param value - The value.
   * @returns The finite number, null otherwise.
   */
  private static readNumber(value: unknown): number | null {
    const parsedText: number = typeof value === 'string' && value.trim() ? Number(value) : Number.NaN
    const numberValue: number = typeof value === 'number' ? value : parsedText
    return Number.isFinite(numberValue) ? numberValue : null
  }

  /**
   * A content value as a web address.
   * @param value - The value.
   * @returns The `http(s)` address, empty otherwise.
   */
  private static readHttpUrl(value: unknown): string {
    const url: string = SiteStructuredDataUtils.readText(value)
    return HTTP_URL.test(url) ? url : ''
  }
}
