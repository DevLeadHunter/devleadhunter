import type { SiteContent } from '@devleadhunter/website-content'

/** A Storyblok blok object (arbitrary fields plus `component` / `_uid`). */
type Blok = Record<string, unknown>

/** Return a trimmed string, or undefined when the value is empty/not a string. */
function str(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

/** Return the value as an array of bloks, or an empty array. */
function list(value: unknown): Blok[] {
  return Array.isArray(value) ? (value as Blok[]) : []
}

/** Return the value as a plain object, or an empty object. */
function obj(value: unknown): Blok {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Blok) : {}
}

/**
 * Locate the native `site_content` blok inside a resolved Storyblok content object.
 *
 * Handles both shapes Storyblok / the API can hand us:
 * - page-wrapped: `{ component: 'page', body: [{ component: 'site_content', … }] }`
 * - bare: the `{ component: 'site_content', … }` blok itself.
 *
 * @param raw - The resolved content (content_json, Storyblok draft, or live bridge edits).
 * @returns The `site_content` blok, or undefined when none is present.
 */
function findSiteContentBlok(raw: Blok): Blok | undefined {
  if (raw?.component === 'site_content') {
    return raw
  }
  const body: Blok[] = list(raw.body)
  return body.find((b): boolean => b?.component === 'site_content')
}

/**
 * Return true when a resolved content object is the Storyblok-native `site_content`
 * representation (Phase 4b) — either page-wrapped or bare.
 *
 * @param raw - The resolved content dict.
 * @returns Whether the content carries a `site_content` blok.
 */
export function isStoryblokSiteContent(raw: Record<string, unknown>): boolean {
  return findSiteContentBlok(raw as Blok) !== undefined
}

/**
 * Bridge — flatten the Storyblok-native `site_content` representation back into the flat
 * `SiteContent` the template layer consumes.
 *
 * Each nested blok list (`site_content_service` / `_review` / `_faq` / `_hours` /
 * `_gallery_item`) is stripped of its `_uid` / `component` and mapped to the flat shape;
 * the palette is read from the nested `theme_palette` blok. Images stay plain URL strings.
 *
 * The DB `content_json` fallback is already flat, so this bridge only runs when demo-host
 * resolves the Storyblok story (live Visual Editor or preview draft).
 *
 * @param raw - The resolved content (page-wrapped or bare `site_content` blok).
 * @returns A flat `SiteContent` (empty/absent keys = hidden sections).
 */
export function storyblokSiteContentToSiteContent(raw: Record<string, unknown>): SiteContent {
  const blok: Blok = findSiteContentBlok(raw as Blok) ?? {}
  const palette: Blok = obj(blok.palette)

  return {
    businessName: str(blok.businessName),
    phone: str(blok.phone),
    email: str(blok.email),
    city: str(blok.city),
    area: str(blok.area),
    subtitle: str(blok.subtitle),
    about: str(blok.about),
    heroImage: str(blok.heroImage),
    aboutImage: str(blok.aboutImage),
    palette: {
      primary: str(palette.primary),
      secondary: str(palette.secondary),
      accent: str(palette.accent),
    },
    gallery: list(blok.gallery)
      .map((item): { url?: string; alt?: string } => ({ url: str(item.url), alt: str(item.alt) }))
      .filter((image): boolean => Boolean(image.url)),
    services: list(blok.services).map((item): { title?: string; description?: string } => ({
      title: str(item.title),
      description: str(item.description),
    })),
    reviews: list(blok.reviews).map((item): { author?: string; rating?: number; text?: string } => ({
      author: str(item.author),
      rating: typeof item.rating === 'number' ? item.rating : undefined,
      text: str(item.text),
    })),
    faq: list(blok.faq).map((item): { question?: string; answer?: string } => ({
      question: str(item.question),
      answer: str(item.answer),
    })),
    openingHours: list(blok.openingHours)
      .map((item): { day?: string; hours?: string } => ({ day: str(item.day), hours: str(item.hours) }))
      .filter((entry): boolean => Boolean(entry.day) || Boolean(entry.hours)),
  }
}
