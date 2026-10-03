import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

const LEGAL_PAGE_SEGMENT: string = 'legal'
const OWNER_VISIT_QUERY: string = 'internal=1'

/**
 * Paths between a site and its legal page, on a demo (`/{slug}/legal`) and on a client's domain (`/legal`).
 */
export class SiteLegalLinkUtils {
  /**
   * The legal page of a site served on its client's domain.
   * @returns The root-relative path.
   */
  static deliveredLegalPath(): string {
    return `/${LEGAL_PAGE_SEGMENT}`
  }

  /**
   * The home page of a demo, keeping the visit's attribution and the owner's tag.
   * @param slug - The demo slug.
   * @param query - The current route query.
   * @returns The path with the carried query, if any.
   */
  static demoHomePath(slug: string, query: Record<string, unknown>): string {
    return SiteLegalLinkUtils.withVisitQuery(`/${slug}`, query)
  }

  /**
   * The legal page of a demo, keeping the visit's attribution and the owner's tag.
   * @param slug - The demo slug.
   * @param query - The current route query.
   * @returns The path with the carried query, if any.
   */
  static demoLegalPath(slug: string, query: Record<string, unknown>): string {
    return SiteLegalLinkUtils.withVisitQuery(`/${slug}/${LEGAL_PAGE_SEGMENT}`, query)
  }

  /**
   * A link to one section of the legal page.
   * @param legalPagePath - The legal page path, its query included.
   * @param anchor - The section anchor.
   * @returns The path ending on the anchor.
   */
  static sectionHref(legalPagePath: string, anchor: string): string {
    return `${legalPagePath}#${anchor}`
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
