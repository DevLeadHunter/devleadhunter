export type Theme = { primary: string; secondary: string; accent: string }

/** Atelier laiton/papier — le laiton porte la signature, l'encre les zones sombres. */
export const defaultTheme: Theme = { primary: '#B8732E', secondary: '#1C1B19', accent: '#2E5B6B' }

export interface HeroBlock {
  component?: string
  title?: string
  subtitle?: string
  phone?: string
  cta_label?: string
  badge?: string
}

export interface TrustBlock {
  component?: string
  items?: Array<{ value?: string; label?: string }>
}

export interface ServicesBlock {
  component?: string
  heading?: string
  subheading?: string
  items?: Array<{ label?: string; description?: string; icon?: string }>
}

export interface WhyUsBlock {
  component?: string
  heading?: string
  items?: Array<{ label?: string }>
}

export interface ContactBlock {
  component?: string
  heading?: string
  subheading?: string
  email?: string
  phone?: string
  city?: string
}
