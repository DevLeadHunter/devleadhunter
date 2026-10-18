import type { SchemaOrgBusinessType, SchemaOrgTradeRule } from '~/types/SiteStructuredData'
import { SCHEMA_ORG_TRADE_RULES, SCHEMA_ORG_TYPE_BY_TEMPLATE } from '~/constants/SchemaOrgBusinessTypes'
import { TextFoldUtils } from '~/utils/TextFoldUtils'

/**
 * The schema.org type of a site's business, from its listing's category, else from the trade its template is drawn for.
 */
export class SchemaOrgBusinessTypeUtils {
  /**
   * The most precise type the business is known to be (« Électricien » is an Electrician, « garage automobile » an AutoRepair).
   * @param category - The listing's category, or null.
   * @param templateId - The site's template.
   * @returns The trade's type; the template's family, then LocalBusiness, when the category names no known trade.
   */
  static resolveBusinessType(category: string | null | undefined, templateId: string): SchemaOrgBusinessType {
    const foldedCategory: string = TextFoldUtils.fold(category ?? '')
    const matchingRule: SchemaOrgTradeRule | undefined = SCHEMA_ORG_TRADE_RULES.find(
      (rule: SchemaOrgTradeRule): boolean =>
        rule.keywords.some((keyword: string): boolean => foldedCategory.includes(keyword)),
    )
    return matchingRule?.type ?? SCHEMA_ORG_TYPE_BY_TEMPLATE[templateId] ?? 'LocalBusiness'
  }
}
