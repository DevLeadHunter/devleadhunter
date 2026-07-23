import { ApiClient } from '~/services/api'
import type { Organization } from '~/types'

const BASE_URL: string = '/api/v1/organizations'

export class OrganizationsService {
  /**
   * Fetch the current user's organization (members included).
   * @returns The organization, or null when the user is not in any.
   */
  static async getMyOrganization(): Promise<Organization | null> {
    return ApiClient.get<Organization | null>(`${BASE_URL}/mine`)
  }

  /**
   * Create an organization owned by the current user.
   * @param name - Organization display name.
   * @returns The created organization.
   */
  static async createOrganization(name: string): Promise<Organization> {
    return ApiClient.post<Organization>(BASE_URL, { name })
  }

  /**
   * Invite an existing DevLeadHunter user (by account email) into the organization.
   * @param email - Account email of the user to add.
   * @returns The updated organization.
   */
  static async inviteMember(email: string): Promise<Organization> {
    return ApiClient.post<Organization>(`${BASE_URL}/members`, { email })
  }

  /**
   * Remove a member from the organization (owner), or leave it (self).
   * @param memberUserId - User id of the member to remove.
   */
  static async removeMember(memberUserId: number): Promise<void> {
    await ApiClient.delete<unknown>(`${BASE_URL}/members/${memberUserId}`)
  }

  /**
   * Delete the organization (owner only) — every member's prospects turn personal again.
   */
  static async deleteOrganization(): Promise<void> {
    await ApiClient.delete<unknown>(BASE_URL)
  }
}
