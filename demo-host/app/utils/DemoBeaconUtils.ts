/**
 * Fire-and-forget beacons to the DevLeadHunter API for notify-worthy demo events,
 * plus the owner-visit guard shared by the demo and video trackers.
 */
export class DemoBeaconUtils {
  /**
   * Whether the current visit is the owner's own — excluded from tracking and beacons.
   * Covers the owner's tagged visits (?internal=1 / ?_edit=1) and the Storyblok
   * Visual Editor preview (?_storyblok=…): editing or video-capturing a site is
   * never a prospect visit, so it must not notify.
   * @returns True when the visit is internal (owner tag or CMS editor preview).
   */
  static isInternalVisit(): boolean {
    if (!import.meta.client) {
      return false
    }
    const params: URLSearchParams = new URLSearchParams(window.location.search)
    return params.get('internal') === '1' || params.get('_edit') === '1' || params.has('_storyblok')
  }

  /**
   * Marketing channel that brought the visit, from a ``?src=`` link value.
   * Email and SMS links stamp their channel; anything else (bookmark, direct) reads as 'direct'.
   * Pure (takes the value, reads no window) so it is safe during SSR.
   * @param source - The raw ``src`` query value (e.g. route.query.src).
   * @returns 'email' or 'sms' when tagged, else 'direct'.
   */
  static channelFromQuery(source: unknown): string {
    return source === 'email' || source === 'sms' ? source : 'direct'
  }

  /**
   * A/B variant a campaign link carries, from its ``?v=`` value. Pure, so it is safe during SSR.
   * @param variant - The raw ``v`` query value (e.g. route.query.v).
   * @returns The variant, or null when the link carries none.
   */
  static variantFromQuery(variant: unknown): string | null {
    return typeof variant === 'string' && variant ? variant : null
  }

  /**
   * A demo-host path carrying the visit's A/B variant and channel, so the next page stays attributed.
   * @param path - The page path (e.g. '/ia/garage-martin').
   * @param variant - The visit's A/B variant, or null.
   * @param channel - The visit's channel; 'direct' adds nothing.
   * @returns The path with its ``v`` and ``src`` query when there are any.
   */
  static attributedPath(path: string, variant: string | null, channel: string): string {
    const params: URLSearchParams = new URLSearchParams()
    if (variant) params.set('v', variant)
    if (channel !== 'direct') params.set('src', channel)
    const query: string = params.toString()
    return query ? `${path}?${query}` : path
  }

  /**
   * Beacon a demo/video behavioural event to the notifications endpoint (best-effort).
   * @param apiBase - DevLeadHunter API base URL.
   * @param slug - Demo slug identifying the prospect.
   * @param event - Event name (e.g. 'demo_cta_click').
   * @param extra - Optional context (label, host, seconds, max_scroll).
   */
  static send(apiBase: string, slug: string, event: string, extra: Record<string, unknown> = {}): void {
    if (!import.meta.client || !apiBase || !slug) {
      return
    }
    const channel: string = DemoBeaconUtils.channelFromQuery(new URLSearchParams(window.location.search).get('src'))
    fetch(`${apiBase}/api/v1/demo-events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ demo_slug: slug, event, channel, ...extra }),
      keepalive: true,
    }).catch((): void => {})
  }
}
