import type { ProspectSearchCandidate } from '~/types/ProspectSearch'
import type { StatusPresentation } from '~/types/StatusPresentation'

export type UiProspectSearchLeadDrawerProps = {
  open: boolean
  candidate: ProspectSearchCandidate | null
  showBack: boolean
}

export type UiProspectSearchLeadDrawerEmits = {
  close: []
  back: []
}

export type ProspectSearchLeadLink = {
  key: string
  label: string
  href: string
  icon: string
  warning: StatusPresentation | null
}

export type ProspectSearchLeadContactDetail = {
  key: string
  label: string
  value: string
  note: string | null
  isLongValue: boolean
}
