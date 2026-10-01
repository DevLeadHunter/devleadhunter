import type { SiteContactPayload, SiteContactResponse } from '~/types/SiteContact'
import { ApiClient } from './api'

const SITE_CONTACT_URL: string = '/api/v1/contact'

/** Messages written on the contact page of the marketing site. */
export class SiteContactService {
  /**
   * Send a visitor's message to the publisher's inbox.
   * @param payload - The visitor's message.
   * @returns The confirmation that the message left.
   * @throws When the visitor sent too many messages or the message could not be mailed.
   */
  static send(payload: SiteContactPayload): Promise<SiteContactResponse> {
    return ApiClient.post<SiteContactResponse>(SITE_CONTACT_URL, payload)
  }
}
