import type { ProspectWebsiteFilter } from '~/types'
import type { ProductModuleKey } from '~/types/ProductModule'
import type { ProspectSearchWaveOptions } from '~/types/ProspectSearchCreatePage'
import type { ProspectSortOrder } from '~/composables/useMyProspectsFilters'

/** How « Mes prospects » shows the prospects while a module is active. */
export type ProspectListModuleOptions = {
  moduleKey: ProductModuleKey
  defaultWebsiteFilter: ProspectWebsiteFilter
  defaultSortOrder: ProspectSortOrder
  showsInboundDemand: boolean
  hasChatWebsiteFilters: boolean
  canBulkScanWebsites: boolean
}

/** How a new prospect search starts while a module is active. */
export type ProspectSearchModuleOptions = {
  moduleKey: ProductModuleKey
  isOnlyWithoutWebsiteByDefault: boolean
  tradeInputPlaceholder: string
  withWebsitesHint: string | null
  loadTradeWaves?(): Promise<ProspectSearchWaveOptions[]>
}
