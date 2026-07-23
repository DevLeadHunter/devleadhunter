/**
 * Props for the UiSidebar component.
 */
export type UiSidebarProps = {
  /** Whether the sidebar is open (mobile off-canvas state). */
  isOpen: boolean
  /** Whether the viewport is mobile size. */
  isMobile: boolean
}

/** One navigation entry of the dashboard sidebar. */
export type UiSidebarLink = {
  /** Route path. */
  to: string
  /** Visible label. */
  label: string
  /** Icon name (lucide via UIcon, or a Font Awesome class). */
  icon: string
}

/** A titled group of sidebar navigation entries. */
export type UiSidebarGroup = {
  /** Mono uppercase group heading (null for the ungrouped top section). */
  heading: string | null
  /** Links of the group. */
  links: UiSidebarLink[]
}

/** Identifier of a DevLeadHunter product module. */
export type DlhModuleKey = 'websites' | 'wallet-cards' | 'freelance-missions'

/** One entry of the module switcher (the shell hosts three activatable modules). */
export type DlhModuleEntry = {
  /** Stable module identifier. */
  key: DlhModuleKey
  /** Visible label. */
  label: string
  /** Icon name (lucide via UIcon). */
  icon: string
  /** Whether the module is not yet available (shows a lock, click = coming soon). */
  locked: boolean
}
