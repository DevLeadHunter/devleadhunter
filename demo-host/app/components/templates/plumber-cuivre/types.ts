/**
 * Types + parsing du contenu Storyblok pour la template 'plumber-cuivre'.
 *
 * Tout le contenu arrive en `Record<string, unknown>` (content_json ou bridge
 * Storyblok) : ce module le convertit en structures typées avec des valeurs
 * par défaut sûres, pour que les sections restent simples et strictement typées.
 */

export interface CuivreTheme {
  primary: string
  secondary: string
  accent: string
}

export const cuivreDefaultTheme: CuivreTheme = {
  primary: '#AE5222',
  secondary: '#1B2A3A',
  accent: '#A07A2E',
}

export interface CuivreHeroContent {
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

export interface CuivreTrustItem {
  value: string
  label: string
}

export interface CuivreEmergencyContent {
  heading: string
  text: string
  phone: string
  availabilityLabel: string
  items: string[]
}

export interface CuivreServiceItem {
  label: string
  description: string
}

export interface CuivreServicesContent {
  heading: string
  subheading: string
  items: CuivreServiceItem[]
}

export interface CuivreCraftItem {
  label: string
  description: string
}

export interface CuivreCraftContent {
  kicker: string
  heading: string
  text: string
  items: CuivreCraftItem[]
}

export interface CuivreAboutContent {
  kicker: string
  heading: string
  text: string
  image: string
  imageCaption: string
  points: string[]
}

export interface CuivreBrandsContent {
  heading: string
  subheading: string
  items: string[]
}

export interface CuivreGalleryItem {
  image: string
  caption: string
}

export interface CuivreGalleryContent {
  heading: string
  subheading: string
  items: CuivreGalleryItem[]
}

export interface CuivreProcessItem {
  title: string
  description: string
}

export interface CuivreProcessContent {
  heading: string
  subheading: string
  items: CuivreProcessItem[]
}

export interface CuivreReviewItem {
  quote: string
  author: string
  rating: number
}

export interface CuivreReviewsContent {
  heading: string
  items: CuivreReviewItem[]
}

export interface CuivreZoneContent {
  heading: string
  city: string
  areaLabel: string
  note: string
}

export interface CuivreFaqItem {
  question: string
  answer: string
}

export interface CuivreFaqContent {
  heading: string
  items: CuivreFaqItem[]
}

export interface CuivreContactContent {
  heading: string
  subheading: string
  phone: string
  email: string
  city: string
  hours: string
  ctaLabel: string
}

/** Contenu complet de la page, prêt à être rendu par les sections. */
export interface CuivrePageContent {
  theme: CuivreTheme
  hero: CuivreHeroContent
  trustItems: CuivreTrustItem[]
  emergency: CuivreEmergencyContent
  services: CuivreServicesContent
  craft: CuivreCraftContent
  about: CuivreAboutContent
  brands: CuivreBrandsContent
  gallery: CuivreGalleryContent
  process: CuivreProcessContent
  reviews: CuivreReviewsContent
  zone: CuivreZoneContent
  faq: CuivreFaqContent
  contact: CuivreContactContent
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
export function parseCuivreContent(content: Record<string, unknown>): CuivrePageContent {
  const rawTheme = (content.theme ?? {}) as UnknownRecord
  const body: UnknownRecord[] = Array.isArray(content.body) ? (content.body as UnknownRecord[]) : []

  const hero = findBlok(body, 'cuivre_hero')
  const trust = findBlok(body, 'cuivre_trust')
  const emergency = findBlok(body, 'cuivre_emergency')
  const services = findBlok(body, 'cuivre_services')
  const craft = findBlok(body, 'cuivre_craft')
  const about = findBlok(body, 'cuivre_about')
  const brands = findBlok(body, 'cuivre_brands')
  const gallery = findBlok(body, 'cuivre_gallery')
  const process = findBlok(body, 'cuivre_process')
  const reviews = findBlok(body, 'cuivre_reviews')
  const zone = findBlok(body, 'cuivre_zone')
  const faq = findBlok(body, 'cuivre_faq')
  const contact = findBlok(body, 'cuivre_contact')

  return {
    theme: {
      primary: str(rawTheme, 'primary', cuivreDefaultTheme.primary),
      secondary: str(rawTheme, 'secondary', cuivreDefaultTheme.secondary),
      accent: str(rawTheme, 'accent', cuivreDefaultTheme.accent),
    },
    hero: {
      badge: str(hero, 'badge', 'Artisan plombier'),
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
      (item: UnknownRecord): CuivreTrustItem => ({
        value: str(item, 'value'),
        label: str(item, 'label'),
      }),
    ),
    emergency: {
      heading: str(emergency, 'heading', 'Une fuite ? On intervient vite.'),
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
        (item: UnknownRecord): CuivreServiceItem => ({
          label: str(item, 'label'),
          description: str(item, 'description'),
        }),
      ),
    },
    craft: {
      kicker: str(craft, 'kicker', "Les règles de l'art"),
      heading: str(craft, 'heading'),
      text: str(craft, 'text'),
      items: items(craft).map(
        (item: UnknownRecord): CuivreCraftItem => ({
          label: str(item, 'label'),
          description: str(item, 'description'),
        }),
      ),
    },
    about: {
      kicker: str(about, 'kicker', 'Votre plombier'),
      heading: str(about, 'heading'),
      text: str(about, 'text'),
      image: str(about, 'image'),
      imageCaption: str(about, 'image_caption'),
      points: items(about, 'points')
        .map((point: UnknownRecord): string => str(point, 'label'))
        .filter((label: string): boolean => label.length > 0),
    },
    brands: {
      heading: str(brands, 'heading', 'Du matériel qui dure'),
      subheading: str(brands, 'subheading'),
      items: items(brands)
        .map((item: UnknownRecord): string => str(item, 'label'))
        .filter((label: string): boolean => label.length > 0),
    },
    gallery: {
      heading: str(gallery, 'heading', 'Nos chantiers récents'),
      subheading: str(gallery, 'subheading'),
      items: items(gallery)
        .map(
          (item: UnknownRecord): CuivreGalleryItem => ({
            image: str(item, 'image'),
            caption: str(item, 'caption'),
          }),
        )
        .filter((item: CuivreGalleryItem): boolean => item.image.length > 0),
    },
    process: {
      heading: str(process, 'heading', 'Comment ça se passe'),
      subheading: str(process, 'subheading'),
      items: items(process).map(
        (item: UnknownRecord): CuivreProcessItem => ({
          title: str(item, 'title'),
          description: str(item, 'description'),
        }),
      ),
    },
    reviews: {
      heading: str(reviews, 'heading', 'Ce que disent nos clients'),
      items: items(reviews)
        .map(
          (item: UnknownRecord): CuivreReviewItem => ({
            quote: str(item, 'quote'),
            author: str(item, 'author', 'Client'),
            rating: typeof item.rating === 'number' ? Math.min(5, Math.max(1, Math.round(item.rating))) : 5,
          }),
        )
        .filter((item: CuivreReviewItem): boolean => item.quote.length > 0),
    },
    zone: {
      heading: str(zone, 'heading', "Secteur d'intervention"),
      city: str(zone, 'city'),
      areaLabel: str(zone, 'area_label'),
      note: str(zone, 'note'),
    },
    faq: {
      heading: str(faq, 'heading', 'Questions fréquentes'),
      items: items(faq)
        .map(
          (item: UnknownRecord): CuivreFaqItem => ({
            question: str(item, 'question'),
            answer: str(item, 'answer'),
          }),
        )
        .filter((item: CuivreFaqItem): boolean => item.question.length > 0),
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
