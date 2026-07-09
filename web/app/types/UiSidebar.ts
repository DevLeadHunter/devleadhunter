/**
 * Props for the UiSidebar component.
 */
export interface UiSidebarProps {
  /** Whether the sidebar is open (mobile off-canvas state). */
  isOpen: boolean
  /** Whether the viewport is mobile size. */
  isMobile: boolean
}

/** One navigation entry of the dashboard sidebar. */
export interface UiSidebarLink {
  /** Route path. */
  to: string
  /** Visible label. */
  label: string
  /** Icon name (lucide via UIcon, or a Font Awesome class). */
  icon: string
}

/** A titled group of sidebar navigation entries. */
export interface UiSidebarGroup {
  /** Mono uppercase group heading (null for the ungrouped top section). */
  heading: string | null
  /** Links of the group. */
  links: UiSidebarLink[]
}
