import type { Prospect } from '~/types'
import { CHAT_WIDGET_PROVIDER_LABELS } from '~/constants/chatWidgetProviders'

/** Reading rules for a prospect's website — a dead or directory site counts as "no real website". */
export class ProspectWebsite {
  private constructor() {}

  /**
   * Whether the prospect has a website that actually responds (not dead, not a directory mini-site).
   * @param prospect - Prospect to evaluate.
   * @returns True when the found website is a real, live one.
   */
  static hasWorkingWebsite(prospect: Prospect): boolean {
    return !!prospect.website && prospect.website_status !== 'dead' && prospect.website_status !== 'placeholder'
  }

  /**
   * Whether a URL was found but points to a dead site or a directory mini-site.
   * @param prospect - Prospect to evaluate.
   * @returns True for the best outreach targets: the prospect already paid for a website once.
   */
  static hasBrokenWebsite(prospect: Prospect): boolean {
    return !!prospect.website && (prospect.website_status === 'dead' || prospect.website_status === 'placeholder')
  }

  /**
   * Whether the last website scan found a chat widget — « déjà équipé » for the receptionist pitch.
   * @param prospect - Prospect to evaluate.
   * @returns True when at least one chat vendor was detected.
   */
  static isChatEquipped(prospect: Prospect): boolean {
    return (prospect.website_equipment_json?.chat_providers.length ?? 0) > 0
  }

  /**
   * Display names of the chat widgets found on the prospect's website.
   * @param prospect - Prospect to read.
   * @returns Vendor names (empty when none or never scanned).
   */
  static chatProviderLabels(prospect: Prospect): string[] {
    return (prospect.website_equipment_json?.chat_providers ?? []).map(
      (provider: string): string => CHAT_WIDGET_PROVIDER_LABELS[provider] ?? provider,
    )
  }
}
