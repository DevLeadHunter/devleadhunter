import type { Prospect } from '~/types'

export type UiProspectDrawerProps = {
  open: boolean
  prospect: Prospect | null
  showBack?: boolean
  startInEdit?: boolean
  browsePositionLabel?: string
  canBrowsePrevious?: boolean
  canBrowseNext?: boolean
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

export type UiProspectDrawerEmits = {
  close: []
  back: []
  browsePrevious: []
  browseNext: []
  updated: [prospect: Prospect]
  deleted: [prospectId: number]
  sendEmail: [prospect: Prospect]
  sendSms: [prospect: Prospect]
  markAsSold: [prospect: Prospect]
  toggleContacted: [prospect: Prospect]
  openSettings: [prospect: Prospect]
}
