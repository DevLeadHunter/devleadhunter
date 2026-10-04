export type ProfileForm = {
  name: string
  email: string
  company_name: string
  company_website_url: string
  contact_phone: string
  contact_email: string
  postal_address: string
  siret: string
  email_accent_color: string
}

export type UiProfileDrawerEmits = {
  close: []
  back: []
}
