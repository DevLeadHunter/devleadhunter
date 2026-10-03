import type { Order } from '~/services/ordersService'

export type UiFinalizeSaleDrawerProps = {
  open: boolean
  order: Order | null
  showBack: boolean
}

/** Editable billing form of the « Finaliser la vente » drawer. */
export type FinalizeSaleForm = {
  name: string
  email: string
  address: string
  zip_code: string
  city: string
  country_code: string
  tax_id: string
  vat_number: string
  amount_euros: number
}

export type ProfessionalLicenseDraft = {
  label: string
  number: string
}

export type StoredProfessionalLicense = {
  label: string
  number: string
  source: string | null
}

export type ProfessionalLicenseState = {
  isQuebecProspect: boolean
  storedLicense: StoredProfessionalLicense | null
}

/** Steps of the sale: review the billing details, then review and send the email. */
export type FinalizeSaleStep = 'billing' | 'email'

export type UiFinalizeSaleDrawerEmits = {
  close: []
  back: []
  updated: [order: Order]
}
