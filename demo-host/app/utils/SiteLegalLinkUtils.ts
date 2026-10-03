import type { SiteLegalPagePaths } from '~/types/SiteLegalPage'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

const LEGAL_PAGE_SEGMENT: string = 'legal'
const PRIVACY_PAGE_SEGMENT: string = 'privacy'
const OWNER_VISIT_QUERY: string = 'internal=1'

/**
 * Paths between a site and its legal pages, on a demo (`/{slug}/legal`, `/{slug}/privacy`) and on a client's
 * domain (`/legal`, `/privacy`).
 */
export class SiteLegalLinkUtils {
  /**
   * The home and legal pages of a site served on its client's domain.
   * @returns The root-relative paths.
   */
  static deliveredPagePaths(): SiteLegalPagePaths {
    return { home: '/', legal: `/${LEGAL_PAGE_SEGMENT}`, privacy: `/${PRIVACY_PAGE_SEGMENT}` }
  }

  /**
   * The home and legal pages of a demo, keeping the visit's attribution and the owner's tag.
   * @param slug - The demo slug.
   * @param query - The current route query.
   * @returns The paths, with the carried query, if any.
   */
  static demoPagePaths(slug: string, query: Record<string, unknown>): SiteLegalPagePaths {
    return {
      home: SiteLegalLinkUtils.withVisitQuery(`/${slug}`, query),
      legal: SiteLegalLinkUtils.withVisitQuery(`/${slug}/${LEGAL_PAGE_SEGMENT}`, query),
      privacy: SiteLegalLinkUtils.withVisitQuery(`/${slug}/${PRIVACY_PAGE_SEGMENT}`, query),
    }
  }

  /**
   * A demo path that keeps the visit's A/B variant and channel, and the owner's tag so their own visit stays untracked.
   * @param path - The root-relative path.
   * @param query - The current route query.
   * @returns The path, with a query only when something is carried.
   */
  private static withVisitQuery(path: string, query: Record<string, unknown>): string {
    const attributedPath: string = DemoBeaconUtils.attributedPath(
      path,
      DemoBeaconUtils.variantFromQuery(query.v),
      DemoBeaconUtils.channelFromQuery(query.src),
    )
    if (query.internal !== '1') return attributedPath
    const separator: string = attributedPath.includes('?') ? '&' : '?'
    return `${attributedPath}${separator}${OWNER_VISIT_QUERY}`
  }
}
