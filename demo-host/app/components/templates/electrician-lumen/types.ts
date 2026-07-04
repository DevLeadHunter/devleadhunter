/**
 * Types + parsing du contenu Storyblok pour la template 'electrician-lumen'.
 *
 * Tout le contenu arrive en `Record<string, unknown>` (content_json ou bridge
 * Storyblok) : ce module le convertit en structures typées avec des valeurs
 * par défaut sûres, pour que les sections restent simples et strictement typées.
 */

export interface LumenTheme {
  primary: string
  secondary: string
  accent: string
}

export const lumenDefaultTheme: LumenTheme = {
  primary: '#FFD400',
  secondary: '#070B14',
  accent: '#FF9F1C',
}

export interface LumenHeroContent {
  badge: string
  title: string
  subtitle: string
  city: string
  phone: string
  ctaCallLabel: string
  ctaQuoteLabel: string
  image: string
  imageCaption: string
  points: string[]
}

export interface LumenTrustItem {
  value: string
  label: string
}

export interface LumenEmergencyContent {
  heading: string
  text: string
  phone: string
  availabilityLabel: string
  items: string[]
}

export interface LumenServiceItem {
  label: string
  description: string
  icon: string
}

export interface LumenServicesContent {
  heading: string
  subheading: string
  items: LumenServiceItem[]
}

export interface LumenSafetyItem {
  code: string
  label: string
}

export interface LumenSafetyContent {
  kicker: string
  heading: string
  text: string
  items: LumenSafetyItem[]
}

export interface LumenGalleryItem {
  image: string
  caption: string
}

export interface LumenGalleryContent {
  heading: string
  subheading: string
  items: LumenGalleryItem[]
}

export interface LumenProcessItem {
  title: string
  description: string
}

export interface LumenProcessContent {
  heading: string
  subheading: string
  items: LumenProcessItem[]
}

export interface LumenReviewItem {
  quote: string
  author: string
  rating: number
}

export interface LumenReviewsContent {
  heading: string
  items: LumenReviewItem[]
}

export interface LumenZoneContent {
  heading: string
  city: string
  areaLabel: string
  note: string
}

export interface LumenFaqItem {
  question: string
  answer: string
}

export interface LumenFaqContent {
  heading: string
  items: LumenFaqItem[]
}

export interface LumenContactContent {
  heading: string
  subheading: string
  phone: string
  email: string
  city: string
  hours: string
  ctaLabel: string
}

/** Contenu complet de la page, prêt à être rendu par les sections. */
export interface LumenPageContent {
  theme: LumenTheme
  hero: LumenHeroContent
  trustItems: LumenTrustItem[]
  emergency: LumenEmergencyContent
  services: LumenServicesContent
  safety: LumenSafetyContent
  gallery: LumenGalleryContent
  process: LumenProcessContent
  reviews: LumenReviewsContent
  zone: LumenZoneContent
  faq: LumenFaqContent
  contact: LumenContactContent
}

type UnknownRecord = Record<string, unknown>

/**
 * Lit une chaîne dans un blok, avec valeur par défaut.
 * @param blok Blok source (potentiellement absent).
 * @param key Clé à lire.
 * @param fallback Valeur par défaut si absente/vide.
 * @returns La chaîne lue ou le fallback.
 */
function str(blok: UnknownRecord | undefined, key: string, fallback = ''): string {
  const value = blok?.[key]
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

/**
 * Lit une liste de bloks enfants dans un blok.
 * @param blok Blok source.
 * @param key Clé de la liste.
 * @returns La liste (vide si absente).
 */
function items(blok: UnknownRecord | undefined, key = 'items'): UnknownRecord[] {
  const value = blok?.[key]
  return Array.isArray(value) ? (value as UnknownRecord[]) : []
}

/**
 * Trouve le premier blok d'un composant donné dans le body de la page.
 * @param body Liste des bloks du body.
 * @param component Nom du composant Storyblok recherché.
 * @returns Le blok trouvé, ou undefined.
 */
function findBlok(body: UnknownRecord[], component: string): UnknownRecord | undefined {
  return body.find((blok: UnknownRecord): boolean => blok.component === component)
}

/**
 * Convertit le content_json brut (ou le contenu live du bridge Storyblok)
 * en contenu de page entièrement typé, avec des défauts sûrs partout.
 * @param content Contenu brut de la story (clé `theme` + `body`).
 * @returns Le contenu typé prêt pour le rendu.
 */
export function parseLumenContent(content: Record<string, unknown>): LumenPageContent {
  const rawTheme = (content.theme ?? {}) as UnknownRecord
  const body: UnknownRecord[] = Array.isArray(content.body) ? (content.body as UnknownRecord[]) : []

  const hero = findBlok(body, 'lumen_hero')
  const trust = findBlok(body, 'lumen_trust')
  const emergency = findBlok(body, 'lumen_emergency')
  const services = findBlok(body, 'lumen_services')
  const safety = findBlok(body, 'lumen_safety')
  const gallery = findBlok(body, 'lumen_gallery')
  const process = findBlok(body, 'lumen_process')
  const reviews = findBlok(body, 'lumen_reviews')
  const zone = findBlok(body, 'lumen_zone')
  const faq = findBlok(body, 'lumen_faq')
  const contact = findBlok(body, 'lumen_contact')

  return {
    theme: {
      primary: str(rawTheme, 'primary', lumenDefaultTheme.primary),
      secondary: str(rawTheme, 'secondary', lumenDefaultTheme.secondary),
      accent: str(rawTheme, 'accent', lumenDefaultTheme.accent),
    },
    hero: {
      badge: str(hero, 'badge', 'Artisan électricien'),
      title: str(hero, 'title'),
      subtitle: str(hero, 'subtitle'),
      city: str(hero, 'city'),
      phone: str(hero, 'phone'),
      ctaCallLabel: str(hero, 'cta_call_label', 'Appeler maintenant'),
      ctaQuoteLabel: str(hero, 'cta_quote_label', 'Demander un devis'),
      image: str(hero, 'image'),
      imageCaption: str(hero, 'image_caption'),
      points: items(hero, 'points')
        .map((point: UnknownRecord): string => str(point, 'label'))
        .filter((label: string): boolean => label.length > 0),
    },
    trustItems: items(trust).map(
      (item: UnknownRecord): LumenTrustItem => ({
        value: str(item, 'value'),
        label: str(item, 'label'),
      }),
    ),
    emergency: {
      heading: str(emergency, 'heading', 'Une panne ? On intervient vite.'),
      text: str(emergency, 'text'),
      phone: str(emergency, 'phone'),
      availabilityLabel: str(emergency, 'availability_label'),
      items: items(emergency)
        .map((item: UnknownRecord): string => str(item, 'label'))
        .filter((label: string): boolean => label.length > 0),
    },
    services: {
      heading: str(services, 'heading', 'Nos services'),
      subheading: str(services, 'subheading'),
      items: items(services).map(
        (item: UnknownRecord): LumenServiceItem => ({
          label: str(item, 'label'),
          description: str(item, 'description'),
          icon: str(item, 'icon', 'panne'),
        }),
      ),
    },
    safety: {
      kicker: str(safety, 'kicker', 'Sécurité & conformité'),
      heading: str(safety, 'heading'),
      text: str(safety, 'text'),
      items: items(safety).map(
        (item: UnknownRecord): LumenSafetyItem => ({
          code: str(item, 'code'),
          label: str(item, 'label'),
        }),
      ),
    },
    gallery: {
      heading: str(gallery, 'heading', 'Nos chantiers récents'),
      subheading: str(gallery, 'subheading'),
      items: items(gallery)
        .map(
          (item: UnknownRecord): LumenGalleryItem => ({
            image: str(item, 'image'),
            caption: str(item, 'caption'),
          }),
        )
        .filter((item: LumenGalleryItem): boolean => item.image.length > 0),
    },
    process: {
      heading: str(process, 'heading', 'Comment ça se passe'),
      subheading: str(process, 'subheading'),
      items: items(process).map(
        (item: UnknownRecord): LumenProcessItem => ({
          title: str(item, 'title'),
          description: str(item, 'description'),
        }),
      ),
    },
    reviews: {
      heading: str(reviews, 'heading', 'Ce que disent nos clients'),
      items: items(reviews)
        .map(
          (item: UnknownRecord): LumenReviewItem => ({
            quote: str(item, 'quote'),
            author: str(item, 'author', 'Client'),
            rating: typeof item.rating === 'number' ? Math.min(5, Math.max(1, Math.round(item.rating))) : 5,
          }),
        )
        .filter((item: LumenReviewItem): boolean => item.quote.length > 0),
    },
    zone: {
      heading: str(zone, 'heading', "Zone d'intervention"),
      city: str(zone, 'city'),
      areaLabel: str(zone, 'area_label'),
      note: str(zone, 'note'),
    },
    faq: {
      heading: str(faq, 'heading', 'Questions fréquentes'),
      items: items(faq)
        .map(
          (item: UnknownRecord): LumenFaqItem => ({
            question: str(item, 'question'),
            answer: str(item, 'answer'),
          }),
        )
        .filter((item: LumenFaqItem): boolean => item.question.length > 0),
    },
    contact: {
      heading: str(contact, 'heading', 'Parlons de votre projet'),
      subheading: str(contact, 'subheading'),
      phone: str(contact, 'phone'),
      email: str(contact, 'email'),
      city: str(contact, 'city'),
      hours: str(contact, 'hours'),
      ctaLabel: str(contact, 'cta_label', 'Appeler maintenant'),
    },
  }
}
