import type { ProspectSource } from '~/types'

export type UiProspectSourceBadgeProps = {
  source: ProspectSource | string
}

export type ProspectSourcePresentation = {
  label: string
  logoUrl: string | null
  icon: string
  bg: string
  text: string
}
