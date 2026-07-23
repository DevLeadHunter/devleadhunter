/**
 * Props & item types for the reusable `UiTabs` component.
 */

/** A single tab entry. */
export type UiTab = {
  key: string
  label: string
  hint?: string
  icon?: string
}

/** Props of the `UiTabs` component. */
export type UiTabsProps = {
  tabs: UiTab[]
  modelValue: string
}
