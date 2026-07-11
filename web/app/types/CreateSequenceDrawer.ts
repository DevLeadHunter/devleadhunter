/**
 * Props for the UiCreateSequenceDrawer component.
 */
export interface CreateSequenceDrawerProps {
  /** Whether the drawer is open. */
  open: boolean
  /** Whether to show the "back" affordance (drawer stacked on another). */
  showBack: boolean
  /** Prospect ids to pre-select when the drawer opens. */
  prospectIds: number[]
}
