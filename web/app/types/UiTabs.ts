/**
 * Props & item types for the reusable `UiTabs` component.
 * @module types/UiTabs
 */

/** A single tab entry. */
export type UiTab = {
  /** Stable key used as the v-model value. */
  key: string
  /** Visible label. */
  label: string
  /** Optional short subtitle shown under the label. */
  hint?: string
  /** Optional Lucide icon name (e.g. ``i-lucide-globe``). Overridden by the ``icon`` slot. */
  icon?: string
}

/** Props of the `UiTabs` component. */
export type UiTabsProps = {
  /** Tabs to render, left to right. */
  tabs: UiTab[]
  /** Currently selected tab key (v-model). */
  modelValue: string
}
