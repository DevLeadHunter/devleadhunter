import type { ProspectCountry } from '~/types'

export type ProspectCountryOption = {
  code: ProspectCountry
  label: string
  flag: string
}

/**
 * Catalog of the countries the prospection pipeline supports (search, card, filters).
 * France stays the default: every prospect created before the Europe support carries it.
 */
export class ProspectCountries {
  private constructor() {}

  static readonly france: ProspectCountryOption = { code: 'FR', label: 'France', flag: '🇫🇷' }

  static readonly catalog: ProspectCountryOption[] = [
    ProspectCountries.france,
    { code: 'CH', label: 'Suisse', flag: '🇨🇭' },
    { code: 'BE', label: 'Belgique', flag: '🇧🇪' },
    { code: 'LU', label: 'Luxembourg', flag: '🇱🇺' },
  ]

  /**
   * Resolve the display option of a country code.
   * @param code - ISO alpha-2 code stored on the prospect (undefined falls back to France).
   * @returns The matching option, France when the code is unknown.
   */
  static option(code: string | undefined | null): ProspectCountryOption {
    const found: ProspectCountryOption | undefined = ProspectCountries.catalog.find(
      (option: ProspectCountryOption): boolean => option.code === (code ?? 'FR'),
    )
    return found ?? ProspectCountries.france
  }

  /**
   * Short display of a country next to a city ("🇨🇭 Suisse"), empty for France to keep French cards unchanged.
   * @param code - ISO alpha-2 code stored on the prospect.
   * @returns The flag + label suffix, or an empty string for France.
   */
  static suffix(code: string | undefined | null): string {
    const option: ProspectCountryOption = ProspectCountries.option(code)
    return option.code === 'FR' ? '' : `${option.flag} ${option.label}`
  }
}
