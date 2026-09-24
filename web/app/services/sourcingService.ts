import { ApiClient } from '~/services/api'
import type { SourcingVertical } from '~/types/Sourcing'

const BASE_URL: string = '/api/v1/sources'

export class SourcingService {
  /**
   * List the Réceptionniste IA target verticals, wave by wave.
   * @returns The verticals in catalog order (wave 1 first).
   */
  static async listVerticals(): Promise<SourcingVertical[]> {
    return ApiClient.get<SourcingVertical[]>(`${BASE_URL}/verticals`)
  }
}
