import type { ProductModuleKey } from '~/types/ProductModule'
import type { ProspectListModuleOptions, ProspectSearchModuleOptions } from '~/types/ProspectingModuleOptions'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'

const WEBSITES_PROSPECT_LIST_OPTIONS: ProspectListModuleOptions = {
  moduleKey: WEBSITES_MODULE_KEY,
  defaultWebsiteFilter: 'no',
  defaultSortOrder: 'recent',
  showsInboundDemand: false,
  hasChatWebsiteFilters: false,
  canBulkScanWebsites: false,
}

const WEBSITES_PROSPECT_SEARCH_OPTIONS: ProspectSearchModuleOptions = {
  moduleKey: WEBSITES_MODULE_KEY,
  isOnlyWithoutWebsiteByDefault: true,
  tradeInputPlaceholder: 'Serrurier, menuisier…',
  withWebsitesHint: null,
}

const registeredListOptions: Map<ProductModuleKey, ProspectListModuleOptions> = new Map()
const registeredSearchOptions: Map<ProductModuleKey, ProspectSearchModuleOptions> = new Map()

/** How the prospect list and the prospect search behave while a module is active (the websites module's by default). */
export class ProspectingOptionsRegistry {
  private constructor() {}

  /**
   * Register how « Mes prospects » shows the prospects for a module, or replace it.
   * @param options - The module's list options.
   */
  static registerListOptions(options: ProspectListModuleOptions): void {
    registeredListOptions.set(options.moduleKey, options)
  }

  /**
   * Register how a new search starts for a module, or replace it.
   * @param options - The module's search options.
   */
  static registerSearchOptions(options: ProspectSearchModuleOptions): void {
    registeredSearchOptions.set(options.moduleKey, options)
  }

  /**
   * The list options of a module.
   * @param moduleKey - The active module.
   * @returns Its options, or the websites module's.
   */
  static listOptionsOf(moduleKey: ProductModuleKey): ProspectListModuleOptions {
    return registeredListOptions.get(moduleKey) ?? WEBSITES_PROSPECT_LIST_OPTIONS
  }

  /**
   * The search options of a module.
   * @param moduleKey - The active module.
   * @returns Its options, or the websites module's.
   */
  static searchOptionsOf(moduleKey: ProductModuleKey): ProspectSearchModuleOptions {
    return registeredSearchOptions.get(moduleKey) ?? WEBSITES_PROSPECT_SEARCH_OPTIONS
  }
}
