import type { Prospect } from '~/types'

export type UiProspectDrawerProps = {
  open: boolean
  prospect: Prospect | null
  showBack?: boolean
}

export type LighthouseGauge = {
  label: string
  score: number | null
  color: string
}

export type ProspectEditForm = {
  name: string
  phone: string
  email: string
  website: string
  address: string
  city: string
  category: string
}
