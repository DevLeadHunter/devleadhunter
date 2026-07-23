import type { Prospect } from '~/types'

/** Local shape of the Google prefill form. */
export type AddProspectPrefillForm = {
  business_name: string
  google_maps_url: string
  city: string
}

export type UiAddProspectDrawerEmits = {
  close: []
  back: []
  created: [prospect: Prospect]
}
