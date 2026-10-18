import type { PostalAddressParts, SchemaOrgPostalAddress } from '~/types/SiteStructuredData'
import { TextFoldUtils } from '~/utils/TextFoldUtils'

const COUNTRY_CODE: RegExp = /^[A-Z]{2}$/
const COUNTRY_NAME_AFTER_COMMA: RegExp =
  /,\s*(france|suisse|schweiz|svizzera|switzerland|belgique|belgie|belgium|luxembourg|canada)\.?$/i
const CANADA_AT_END: RegExp = /,?\s*\bcanada\.?$/i
const POSTAL_CODE_AND_LOCALITY_AT_END: RegExp = /(?:^|,\s*)(?:[A-Z]{1,2}-)?(\d{4,5})\s+([^,\d][^,]*)$/
const CANADIAN_POSTAL_CODE: RegExp = /\b([A-Z]\d[A-Z])\s?(\d[A-Z]\d)\b/i
const CANADIAN_PROVINCE: RegExp = /\b(AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b/gi
const LETTER: RegExp = /\p{L}/u

/**
 * A listing's one-line address (« 9 Rue de l'Aurence, 87000 Limoges ») read into the parts of a schema.org address.
 */
export class SchemaOrgPostalAddressUtils {
  /**
   * The address of the business, from what its site's content holds.
   * @param address - The listing's address line, empty when unknown.
   * @param city - The town the site names.
   * @param country - The business's ISO country code, empty when unknown.
   * @returns The address with only the parts the line or the town really tell, null when neither is known.
   */
  static buildPostalAddress(address: string, city: string, country: string): SchemaOrgPostalAddress | null {
    const line: string = address.normalize('NFC').replace(/\s+/g, ' ').trim()
    const town: string = city.normalize('NFC').trim()
    const countryCode: string = COUNTRY_CODE.test(country) ? country : ''
    const parts: PostalAddressParts =
      countryCode === 'CA'
        ? SchemaOrgPostalAddressUtils.readCanadianParts(line, town)
        : SchemaOrgPostalAddressUtils.readEuropeanParts(line)

    const locality: string = parts.locality || town
    const isStreetOnlyTheTown: boolean = TextFoldUtils.fold(parts.street) === TextFoldUtils.fold(locality)
    const street: string = LETTER.test(parts.street) && !isStreetOnlyTheTown ? parts.street : ''
    if (!street && !locality) return null

    const postalAddress: SchemaOrgPostalAddress = { '@type': 'PostalAddress' }
    if (street) postalAddress.streetAddress = street
    if (parts.postalCode) postalAddress.postalCode = parts.postalCode
    if (locality) postalAddress.addressLocality = locality
    if (parts.region) postalAddress.addressRegion = parts.region
    if (countryCode) postalAddress.addressCountry = countryCode
    return postalAddress
  }

  /**
   * A European line, its postal code and town at the end (« Rue des Draizes 51, 2000 Neuchâtel », « L-1450 Luxembourg »).
   * @param line - The address line.
   * @returns Its parts; a line with commas but no postal code (a list of markets) gives no street.
   */
  private static readEuropeanParts(line: string): PostalAddressParts {
    const withoutCountry: string = SchemaOrgPostalAddressUtils.removeCountryName(line, COUNTRY_NAME_AFTER_COMMA)
    const match: RegExpMatchArray | null = withoutCountry.match(POSTAL_CODE_AND_LOCALITY_AT_END)
    if (match?.index === undefined) {
      return { street: withoutCountry.includes(',') ? '' : withoutCountry, postalCode: '', locality: '', region: '' }
    }

    return {
      street: withoutCountry.slice(0, match.index).trim(),
      postalCode: match[1] ?? '',
      locality: (match[2] ?? '').trim(),
      region: '',
    }
  }

  /**
   * A Québec line, with or without commas (« 5 Rue Saint-Alphonse Trois-Rivières Qc Canada G8T 7R2 »).
   * @param line - The address line.
   * @param town - The town the site names, cut from the end of a line without commas.
   * @returns Its parts.
   */
  private static readCanadianParts(line: string, town: string): PostalAddressParts {
    const postalMatch: RegExpMatchArray | null = line.match(CANADIAN_POSTAL_CODE)
    const postalCode: string = postalMatch ? `${postalMatch[1]} ${postalMatch[2]}`.toUpperCase() : ''
    const withoutPostalCode: string = postalMatch ? line.replace(postalMatch[0], ' ') : line

    const lastProvinceMatch: RegExpMatchArray | undefined = [...withoutPostalCode.matchAll(CANADIAN_PROVINCE)].at(-1)
    const region: string = lastProvinceMatch?.[1]?.toUpperCase() ?? ''
    const withoutProvince: string =
      lastProvinceMatch?.index === undefined
        ? withoutPostalCode
        : `${withoutPostalCode.slice(0, lastProvinceMatch.index)} ${withoutPostalCode.slice(lastProvinceMatch.index + lastProvinceMatch[0].length)}`

    const namesProvinceOrPostalCode: boolean = Boolean(postalCode || region)
    const rest: string = SchemaOrgPostalAddressUtils.removeCountryName(
      withoutProvince,
      namesProvinceOrPostalCode ? CANADA_AT_END : COUNTRY_NAME_AFTER_COMMA,
    )

    const commaParts: string[] = rest
      .split(',')
      .map((part: string): string => part.trim())
      .filter(Boolean)
    if (commaParts.length > 1) {
      return { street: commaParts[0] ?? '', postalCode, locality: commaParts[1] ?? '', region }
    }

    const endsWithTown: boolean = town.length > 0 && TextFoldUtils.fold(rest).endsWith(TextFoldUtils.fold(town))
    return {
      street: endsWithTown ? rest.slice(0, rest.length - town.length).trim() : rest,
      postalCode,
      locality: endsWithTown ? town : '',
      region,
    }
  }

  /**
   * The line without the country's name a listing sometimes writes (« …, Neuchâtel, Suisse », never « rue du Luxembourg »).
   * @param line - The address line.
   * @param countryName - Where the line's country name may stand.
   * @returns The line, its spaces and trailing commas tidied.
   */
  private static removeCountryName(line: string, countryName: RegExp): string {
    const tidied: string = line.replace(/\s+/g, ' ').replace(/[\s,]+$/, '')
    return tidied
      .replace(countryName, '')
      .replace(/[\s,]+$/, '')
      .trim()
  }
}
