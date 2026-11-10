import type { ProductModuleKey } from '~/types/ProductModule'

export type UiSidebarProps = {
  isOpen: boolean
  isMobile: boolean
}

/** Identifier of a sidebar counter badge: the core's `pendingLeads`, or one a module brings. */
export type UiSidebarCounterKey = string

/** One navigation entry of the dashboard sidebar. */
export type UiSidebarLink = {
  to: string
  label: string
  icon: string
  counterKey?: UiSidebarCounterKey
}

export type UiSidebarCounter = {
  count: number
  description: string
}

/** A titled group of sidebar navigation entries. */
export type UiSidebarGroup = {
  heading: string | null
  links: UiSidebarLink[]
}

/** Identifier of a DevLeadHunter product module. */
export type DlhModuleKey = ProductModuleKey

/** The prominent call-to-action button a module puts at the top of the sidebar. */
export type DlhModulePrimaryCta = {
  label: string
  to: string
  icon: string
}

/**
 * A full product module: its switcher identity plus the navigation it owns.
 * Selecting a module swaps the whole sidebar to `navGroups` and lands on `home`.
 */
export type DlhModule = {
  key: DlhModuleKey
  label: string
  icon: string
  locked: boolean
  home: string
  primaryCta: DlhModulePrimaryCta | null
  navGroups: UiSidebarGroup[]
}

/** A counter badge a module computes for its own navigation links (read inside a computed: it may use stores). */
export type DashboardModuleSidebarCounter = {
  key: UiSidebarCounterKey
  read: () => UiSidebarCounter
}

/** What a product module layer registers to appear in the dashboard: switcher entry, navigation, labels of its data. */
export type DashboardModuleDefinition = {
  key: DlhModuleKey
  label: string
  icon: string
  home: string
  primaryCta: DlhModulePrimaryCta | null
  navGroups: UiSidebarGroup[]
  sidebarCounters?: DashboardModuleSidebarCounter[]
  activityCategoryLabels?: Record<string, string>
  orderProductLabels?: Record<string, string>
  describeProspectsWithoutOffer?: (prospectNames: string[]) => string
}
