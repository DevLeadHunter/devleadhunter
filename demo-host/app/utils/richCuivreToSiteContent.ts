import type { SiteContent } from '@devleadhunter/website-content'

/** A blok object inside the legacy rich `content_json.body` array. */
type Blok = Record<string, unknown>

/** Return a trimmed string, or undefined when the value is empty/not a string. */
function str(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

/** Return the value as an array of bloks, or an empty array. */
function list(value: unknown): Blok[] {
  return Array.isArray(value) ? (value as Blok[]) : []
}

/**
 * Bridge — derive a shared `SiteContent` from the legacy rich plumber-cuivre content
 * (the `cuivre_*` bloks stored in `content_json` / Storyblok). This lets the extends'd
 * `PlumberCuivreRoot` (which renders a typed `SiteContent`) consume the existing tunnel
 * data without changing the API or Storyblok.
 *
 * Temporary by design: once the API produces `SiteContent` directly (Phase 4b), demo-host
 * will pass it through and this bridge is deleted.
 *
 * @param raw - The resolved content dict (content_json, Storyblok draft, or live bridge edits).
 * @param businessName - The site business name (fallback for the hero title).
 * @returns A `SiteContent` built from the rich cuivre bloks (empty keys = hidden sections).
 */
export function richCuivreToSiteContent(
  raw: Record<string, unknown>,
  businessName: string,
): SiteContent {
  const body: Blok[] = list(raw.body)
  const blok = (component: string): Blok => body.find((b) => b?.component === component) ?? {}

  const hero: Blok = blok('cuivre_hero')
  const about: Blok = blok('cuivre_about')
  const services: Blok = blok('cuivre_services')
  const gallery: Blok = blok('cuivre_gallery')
  const reviews: Blok = blok('cuivre_reviews')
  const faq: Blok = blok('cuivre_faq')
  const zone: Blok = blok('cuivre_zone')
  const contact: Blok = blok('cuivre_contact')
  const theme: Blok = raw.theme && typeof raw.theme === 'object' ? (raw.theme as Blok) : {}

  const hours: string | undefined = str(contact.hours)

  return {
    businessName: businessName || str(hero.title),
    phone: str(contact.phone) ?? str(hero.phone),
    email: str(contact.email),
    city: str(hero.city) ?? str(contact.city) ?? str(zone.city),
    area: str(zone.areaLabel),
    subtitle: str(hero.subtitle),
    about: str(about.text),
    heroImage: str(hero.image),
    aboutImage: str(about.image),
    palette: {
      primary: str(theme.primary),
      secondary: str(theme.secondary),
      accent: str(theme.accent),
    },
    gallery: list(gallery.items)
      .map((item) => ({ url: str(item.image), alt: str(item.caption) }))
      .filter((image) => Boolean(image.url)),
    services: list(services.items).map((item) => ({
      title: str(item.label),
      description: str(item.description),
    })),
    reviews: list(reviews.items).map((item) => ({
      text: str(item.quote),
      author: str(item.author),
      rating: typeof item.rating === 'number' ? item.rating : undefined,
    })),
    faq: list(faq.items).map((item) => ({
      question: str(item.question),
      answer: str(item.answer),
    })),
    // The legacy contact.hours is a single formatted string; keep it as one entry so the
    // template's opening-hours formatter surfaces it (day is unknown here).
    openingHours: hours ? [{ hours }] : [],
  }
}
