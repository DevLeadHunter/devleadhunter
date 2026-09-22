export type UiSidebarProps = {
  isOpen: boolean
  isMobile: boolean
}

/** One navigation entry of the dashboard sidebar. */
export type UiSidebarLink = {
  to: string
  label: string
  icon: string
}

/** A titled group of sidebar navigation entries. */
export type UiSidebarGroup = {
  heading: string | null
  links: UiSidebarLink[]
}

/** Identifier of a DevLeadHunter product module. */
export type DlhModuleKey = 'websites' | 'ai-assistant' | 'wallet-cards' | 'freelance-missions'

/** One entry of the module switcher (the shell hosts several activatable modules). */
export type DlhModuleEntry = {
  key: DlhModuleKey
  label: string
  icon: string
  locked: boolean
}

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
