import type { Component } from 'vue'
import type { Prospect } from '~/types'
import type { ProductModuleKey } from '~/types/ProductModule'

/** What the prospect drawer hands to a module's block or button; `openingId` bumps each time it opens on a prospect. */
export type ProspectDrawerExtensionProps = {
  prospect: Prospect
  openingId: number
}

/** The events a module block of the prospect drawer may emit (the drawer passes the prospect on to the lists). */
export type ProspectDrawerSectionEmits = {
  updated: [prospect: Prospect]
}

/** What a module block decides from whether it shows. */
export type ProspectDrawerSectionContext = {
  prospect: Prospect
  activeModuleKey: ProductModuleKey
}

/** A block a product module adds to the prospect drawer, under « Informations ». */
export type ProspectDrawerSectionRegistration = {
  key: string
  moduleKey: ProductModuleKey
  component: Component
  isShown(context: ProspectDrawerSectionContext): boolean
}

/** The footer's main button while the module is the active one (the core's demo-site button otherwise). */
export type ProspectDrawerPrimaryActionRegistration = {
  moduleKey: ProductModuleKey
  component: Component
}
