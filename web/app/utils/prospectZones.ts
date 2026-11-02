import type { ProspectCountry, ProspectRegion, ProspectZone } from '~/types'
import type { ProspectCountryOption } from '~/utils/prospectCountries'
import { ProspectCountries } from '~/utils/prospectCountries'

export type ProspectZoneOption = {
  code: ProspectZone
  label: string
  flag: string
  country: ProspectCountry
  region: ProspectRegion | null
  departmentCode: string | null
}

/** What places a prospect, a lead or a search: its country and its overseas department, as the API sends them. */
export type ProspectZonePlace = {
  country?: string | null
  region?: string | null
}

/**
 * Catalog of the zones the prospection works in (search, map, flags): every supported country, and Martinique,
 * French for the law but with its own clock, its own communes and its own place on the map, as Québec has.
 */
export class ProspectZones {
  private constructor() {}

  static readonly france: ProspectZoneOption = ProspectZones.zoneOfCountry(ProspectCountries.france)

  static readonly martinique: ProspectZoneOption = {
    code: 'MQ',
    label: 'Martinique',
    flag: '🇲🇶',
    country: 'FR',
    region: 'MQ',
    departmentCode: '972',
  }

  static readonly catalog: ProspectZoneOption[] = [
    ...ProspectCountries.catalog.map(
      (option: ProspectCountryOption): ProspectZoneOption => ProspectZones.zoneOfCountry(option),
    ),
    ProspectZones.martinique,
  ]

  /**
   * Resolve the display option of a zone code.
   * @param code - A country's code (« CH ») or an overseas department's (« MQ »).
   * @returns The matching option, France when the code is unknown.
   */
  static option(code: string | undefined | null): ProspectZoneOption {
    const found: ProspectZoneOption | undefined = ProspectZones.catalog.find(
      (option: ProspectZoneOption): boolean => option.code === (code ?? 'FR'),
    )
    return found ?? ProspectZones.france
  }

  /**
   * The zone of a prospect, a lead or a search: its overseas department when the catalog has it, else its country.
   * @param place - Country and overseas department of the prospect, the lead or the search.
   * @returns The zone's code.
   */
  static of(place: ProspectZonePlace | null | undefined): ProspectZone {
    const department: ProspectZoneOption | undefined = ProspectZones.catalog.find(
      (option: ProspectZoneOption): boolean => option.region !== null && option.region === place?.region,
    )
    return department?.code ?? ProspectCountries.option(place?.country).code
  }

  /**
   * Label of a zone next to a city (« Martinique », « Suisse »), empty for France so French cards stay unchanged.
   * @param code - The zone's code.
   * @returns The zone's label, or an empty string for mainland France.
   */
  static suffix(code: string | undefined | null): string {
    const option: ProspectZoneOption = ProspectZones.option(code)
    return option.code === ProspectZones.france.code ? '' : option.label
  }

  /**
   * The zone a whole country makes.
   * @param option - The country's option.
   * @returns The same option, as a zone.
   */
  private static zoneOfCountry(option: ProspectCountryOption): ProspectZoneOption {
    return { ...option, country: option.code, region: null, departmentCode: null }
  }
}
