import type { Prospect } from '~/types'

export type UiProspectSettingsDrawerProps = {
  open: boolean
  prospect: Prospect | null
  showBack?: boolean
}

/** Editable source-URL fields of the settings form. */
export type ProspectSettingsForm = {
  facebook_url: string
  google_maps_url: string
}

export type UiProspectSettingsDrawerEmits = {
  close: []
  back: []
  updated: [prospect: Prospect]
}
