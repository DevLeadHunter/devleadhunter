import type { ProductModuleKey } from '~/types/ProductModule'

export type SettingsPageRequiredModuleFeature = 'email-templates' | 'sms-templates' | 'presenter-video'

export type SettingsNavLink = {
  to: string
  label: string
  icon: string
  adminOnly?: boolean
  superAdminOnly?: boolean
  requiredModuleFeature?: SettingsPageRequiredModuleFeature
  labelOutsideWebsitesModule?: string
  ownerModuleKey?: ProductModuleKey
}

export type SettingsNavGroup = {
  heading: string
  entries: SettingsNavLink[]
  adminOnly?: boolean
}

/** A settings page a product module adds to the « Paramètres » panel, at the end of one of its groups. */
export type ModuleSettingsNavEntry = {
  moduleKey: ProductModuleKey
  groupHeading: string
  entry: SettingsNavLink
}
