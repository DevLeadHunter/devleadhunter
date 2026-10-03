/** Establishment block returned by recherche-entreprises.api.gouv.fr. */
export type RegistryEstablishment = {
  siret?: string
  adresse?: string
  code_postal?: string
  libelle_commune?: string
  numero_voie?: string
  type_voie?: string
  libelle_voie?: string
}

/** Company block returned by recherche-entreprises.api.gouv.fr. */
export type RegistryCompany = {
  siren: string
  nom_complet: string
  nom_raison_sociale?: string
  siege?: RegistryEstablishment
  matching_etablissements?: RegistryEstablishment[]
  tva?: string[]
}

export type RegistrySearchResponse = {
  results: RegistryCompany[]
}

/** Billing fields that can be prefilled from a registry lookup. */
export type CompanyBillingPrefill = {
  name: string
  address: string
  zip_code: string
  city: string
  tax_id: string
  vat_number: string | null
}

export type TaxIdLookupStatus = 'idle' | 'loading' | 'verified' | 'not-found' | 'error'

export type TaxIdLookupInputProps = {
  modelValue: string
  inputId?: string
  placeholder?: string
  disabled?: boolean
  acceptsSiren?: boolean
  hint?: string
}
