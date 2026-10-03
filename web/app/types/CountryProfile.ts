import type { ProspectCountry } from '~/types'

export type CountryProfile = {
  code: ProspectCountry
  label: string
  currency: string
  dial_code: string
  postal_code_pattern: string
  postal_code_example: string
  tax_id_label: string
  tax_id_example: string
  tax_id_required: boolean
  sms_prospecting_open: boolean
}
