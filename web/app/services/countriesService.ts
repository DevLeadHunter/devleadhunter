import type { CountryProfile } from '~/types/CountryProfile'
import { ApiClient } from './api'

/** Reads the countries open to prospection and their facts (fiscal identifier, postal code shape, currency). */
export class CountriesService {
  /**
   * List the countries open to prospection, France first.
   *
   * @returns One profile per open country.
   */
  static list(): Promise<CountryProfile[]> {
    return ApiClient.get<CountryProfile[]>('/api/v1/countries')
  }
}
