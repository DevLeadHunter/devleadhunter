import type { SiteContent } from '@devleadhunter/website-content'

/** A Storyblok blok object: arbitrary content fields plus `component` / `_uid`. */
type Blok = Record<string, unknown>

/**
 * Bridge between the Storyblok-native `site_content` blok tree and the flat `SiteContent`
 * the template layers consume.
 *
 * The DB `content_json` fallback is already flat, so this only runs when demo-host resolves
 * the Storyblok story itself (live Visual Editor or preview draft).
 */
export class StoryblokSiteContentBridge {
  /**
   * Read a Storyblok text field.
   *
   * @param value - Raw field value.
   * @returns The string, or undefined when it is empty or not a string.
   */
  private static readString(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim() ? value : undefined
  }

  /**
   * Read a repeatable blok field.
   *
   * @param value - Raw field value.
   * @returns The bloks, or an empty array when the field is absent.
   */
  private static readBlokList(value: unknown): Blok[] {
    return Array.isArray(value) ? (value as Blok[]) : []
  }

  /**
   * Read an object field.
   *
   * @param value - Raw field value.
   * @returns The object, or an empty object when the field is absent or is an array.
   */
  private static readBlok(value: unknown): Blok {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Blok) : {}
  }

  /**
   * Read a single-blok field, which Storyblok returns as a LIST once the story has been
   * republished from the editor even though our API writes it as a plain object.
   *
   * @param value - Raw field value (object or one-element list).
   * @returns The blok, or an empty object.
   */
  private static readSingleBlok(value: unknown): Blok {
    return Array.isArray(value) ? this.readBlok(value[0]) : this.readBlok(value)
  }

  /**
   * Locate the `site_content` blok, which arrives either page-wrapped (`{ component: 'page', body: [ … ] }`) or bare.
   *
   * @param raw - Resolved content (content_json, Storyblok draft, or live bridge edits).
   * @returns The `site_content` blok, or undefined when none is present.
   */
  private static findSiteContentBlok(raw: Blok): Blok | undefined {
    if (raw?.component === 'site_content') {
      return raw
    }
    return this.readBlokList(raw.body).find((blok): boolean => blok?.component === 'site_content')
  }

  /**
   * Tell whether a resolved content object is the Storyblok-native representation rather than flat `SiteContent`.
   *
   * @param raw - Resolved content object.
   * @returns Whether the content carries a `site_content` blok.
   */
  static isStoryblokSiteContent(raw: Record<string, unknown>): boolean {
    return this.findSiteContentBlok(raw as Blok) !== undefined
  }

  /**
   * Flatten the Storyblok-native representation into the `SiteContent` a template layer renders.
   *
   * Nested blok lists lose their `_uid` / `component`, the palette is read from its own blok,
   * and images stay plain URL strings.
   *
   * @param raw - Resolved content (page-wrapped or bare `site_content` blok).
   * @returns A flat `SiteContent` — absent keys mean hidden sections.
   */
  static toSiteContent(raw: Record<string, unknown>): SiteContent {
    const blok: Blok = this.findSiteContentBlok(raw as Blok) ?? {}
    const palette: Blok = this.readSingleBlok(blok.palette)

    return {
      businessName: this.readString(blok.businessName),
      phone: this.readString(blok.phone),
      email: this.readString(blok.email),
      city: this.readString(blok.city),
      area: this.readString(blok.area),
      subtitle: this.readString(blok.subtitle),
      about: this.readString(blok.about),
      heroBadge: this.readString(blok.heroBadge),
      heroPoints: this.readBlokList(blok.heroPoints)
        .map((item): string | undefined => this.readString(item.text))
        .filter((text): text is string => Boolean(text)),
      ctaCallLabel: this.readString(blok.ctaCallLabel),
      ctaQuoteLabel: this.readString(blok.ctaQuoteLabel),
      trustItems: this.readBlokList(blok.trustItems)
        .map((item): { value?: string; label?: string } => ({
          value: this.readString(item.value),
          label: this.readString(item.label),
        }))
        .filter((item): boolean => Boolean(item.value) || Boolean(item.label)),
      servicesHeading: this.readString(blok.servicesHeading),
      galleryHeading: this.readString(blok.galleryHeading),
      reviewsHeading: this.readString(blok.reviewsHeading),
      faqHeading: this.readString(blok.faqHeading),
      aboutHeading: this.readString(blok.aboutHeading),
      contactHeading: this.readString(blok.contactHeading),
      logo: this.readString(blok.logo),
      heroImage: this.readString(blok.heroImage),
      aboutImage: this.readString(blok.aboutImage),
      palette: {
        primary: this.readString(palette.primary),
        secondary: this.readString(palette.secondary),
        accent: this.readString(palette.accent),
      },
      gallery: this.readBlokList(blok.gallery)
        .map((item): { url?: string; alt?: string } => ({
          url: this.readString(item.url),
          alt: this.readString(item.alt),
        }))
        .filter((image): boolean => Boolean(image.url)),
      services: this.readBlokList(blok.services).map((item): { title?: string; description?: string } => ({
        title: this.readString(item.title),
        description: this.readString(item.description),
      })),
      reviews: this.readBlokList(blok.reviews).map((item): { author?: string; rating?: number; text?: string } => ({
        author: this.readString(item.author),
        rating: typeof item.rating === 'number' ? item.rating : undefined,
        text: this.readString(item.text),
      })),
      faq: this.readBlokList(blok.faq).map((item): { question?: string; answer?: string } => ({
        question: this.readString(item.question),
        answer: this.readString(item.answer),
      })),
      openingHours: this.readBlokList(blok.openingHours)
        .map((item): { day?: string; hours?: string } => ({
          day: this.readString(item.day),
          hours: this.readString(item.hours),
        }))
        .filter((entry): boolean => Boolean(entry.day) || Boolean(entry.hours)),
      beforeAfter: this.readBlokList(blok.beforeAfter)
        .map((item): { before?: string; after?: string; label?: string } => ({
          before: this.readString(item.before),
          after: this.readString(item.after),
          label: this.readString(item.label),
        }))
        .filter((pair): boolean => Boolean(pair.before) || Boolean(pair.after)),
      social: this.readBlokList(blok.social)
        .map((item): { network?: string; url?: string } => ({
          network: this.readString(item.network),
          url: this.readString(item.url),
        }))
        .filter((link): boolean => Boolean(link.url)),
    }
  }
}
