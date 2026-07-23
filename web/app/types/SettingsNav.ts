export type SettingsNavLink = {
  kind: 'link'
  to: string
  label: string
  icon: string
  adminOnly?: boolean
}

export type SettingsNavAction = {
  kind: 'action'
  action: 'send-policy'
  label: string
  icon: string
  adminOnly?: boolean
}

export type SettingsNavEntry = SettingsNavLink | SettingsNavAction

export type SettingsNavGroup = {
  heading: string
  entries: SettingsNavEntry[]
  adminOnly?: boolean
}
