export type Theme = { primary: string; secondary: string; accent: string }

/** Signature — pétrole/encre/corail, photographique. Le corail porte l'urgence et les CTA. */
export const defaultTheme: Theme = { primary: '#0F5257', secondary: '#14181C', accent: '#E8552D' }

export interface HeroBlock {
  component?: string
  title?: string
  subtitle?: string
  badge?: string
  cta_label?: string
  phone?: string
  city?: string
  image?: string
  points?: string[]
}

export interface TrustBlock {
  component?: string
  items?: { value?: string; label?: string }[]
}

export interface ServicesBlock {
  component?: string
  heading?: string
  subheading?: string
  items?: { label?: string; description?: string; icon?: string }[]
}

export interface StepsBlock {
  component?: string
  heading?: string
  subheading?: string
  items?: { title?: string; description?: string; icon?: string }[]
}

export interface GalleryBlock {
  component?: string
  heading?: string
  subheading?: string
  items?: { image?: string; caption?: string; location?: string }[]
}

export interface BeforeAfterBlock {
  component?: string
  heading?: string
  subheading?: string
  caption?: string
  before_image?: string
  after_image?: string
  before_label?: string
  after_label?: string
}

export interface StoryBlock {
  component?: string
  kicker?: string
  heading?: string
  paragraphs?: string[]
  values?: { label?: string; description?: string; icon?: string }[]
  stats?: { value?: string; label?: string }[]
  image?: string
  signature_name?: string
  signature_role?: string
}

export interface TestimonialsBlock {
  component?: string
  heading?: string
  items?: { quote?: string; author?: string; location?: string; rating?: number }[]
}

export interface FaqBlock {
  component?: string
  heading?: string
  items?: { question?: string; answer?: string }[]
}

export interface UrgencyBlock {
  component?: string
  heading?: string
  subheading?: string
  phone?: string
}

export interface ContactBlock {
  component?: string
  heading?: string
  subheading?: string
  email?: string
  phone?: string
  city?: string
  hours?: string
}
