import type { DemoSiteTemplate } from '~/services/demoSiteService'

/**
 * Lowercase a trade string and strip its accents for keyword matching.
 * @param value - Raw trade or category label.
 * @returns The normalized string.
 */
function normalizeTrade(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
}

/**
 * Whether a template targets the given trade, comparing its trade keywords loosely.
 * @param template - Template to test.
 * @param trade - Targeted trade, or null when none is known yet.
 * @returns True when one of the template's keywords matches the trade.
 */
export function isTemplateRecommendedFor(template: DemoSiteTemplate, trade: string | null): boolean {
  if (!trade) return false
  const normalizedTrade: string = normalizeTrade(trade)
  if (!normalizedTrade) return false
  return (template.trades ?? []).some((keyword: string): boolean => {
    const normalizedKeyword: string = normalizeTrade(keyword)
    return normalizedTrade.includes(normalizedKeyword) || normalizedKeyword.includes(normalizedTrade)
  })
}

/**
 * Templates a user may pick: the hidden ones are left out, except the one already in use.
 * @param templates - Templates in their catalog order.
 * @param currentTemplateId - Template the site or the form already uses, or null when none.
 * @returns The pickable templates, catalog order kept.
 */
export function filterSelectableTemplates(
  templates: DemoSiteTemplate[],
  currentTemplateId: string | null,
): DemoSiteTemplate[] {
  return templates.filter(
    (template: DemoSiteTemplate): boolean => !template.is_hidden || template.id === currentTemplateId,
  )
}

/**
 * Templates with the ones recommended for the trade bubbled to the top.
 * @param templates - Templates in their catalog order.
 * @param trade - Targeted trade, or null when none is known yet.
 * @returns A new ordered list; the catalog order is kept inside each group.
 */
export function sortTemplatesByRecommendation(templates: DemoSiteTemplate[], trade: string | null): DemoSiteTemplate[] {
  if (!trade) return templates
  const recommended: DemoSiteTemplate[] = templates.filter((template: DemoSiteTemplate): boolean =>
    isTemplateRecommendedFor(template, trade),
  )
  const others: DemoSiteTemplate[] = templates.filter(
    (template: DemoSiteTemplate): boolean => !isTemplateRecommendedFor(template, trade),
  )
  return [...recommended, ...others]
}
