import type { ComputedRef, Ref } from 'vue'
import type { DemoPreviewIdentity } from '~/types/DemoPreviewIdentity'

/**
 * Live-edit overrides pushed by an embedder's preview iframe via `postMessage`.
 *
 * The dashboard demo-site page acts as an editor, and the dibodev.fr workshop shows a visitor his own
 * business on a showroom demo: colour, photo-order, template, section-card and identity changes are
 * applied instantly on the REAL published site (no regeneration, no reload) by merging these
 * overrides into the rendered content. Nothing is persisted here — saving still goes through the
 * API, which regenerates the published content.
 */
/** One curated card of the editable section (food « Nos spécialités »): title, blurb, photo. */
export type DemoPreviewServiceCard = {
  title: string
  description: string
  image: string
}

export type DemoPreviewOverrides = {
  templateId: string | null
  palette: Record<string, string> | null
  photos: string[] | null
  services: DemoPreviewServiceCard[] | null
  identity: DemoPreviewIdentity | null
}

/** Palette keys the dashboard can override — mirrors the theme contract used at generation. */
const PALETTE_KEYS: string[] = ['primary', 'secondary', 'accent']

/** Hard caps keeping a malicious or buggy message from bloating the page. */
const MAX_PHOTOS: number = 30
const MAX_PHOTO_LENGTH: number = 2_000_000
const MAX_TEMPLATE_ID_LENGTH: number = 64
const MAX_SERVICE_CARDS: number = 12
const MAX_SERVICE_TITLE_LENGTH: number = 120
const MAX_SERVICE_DESCRIPTION_LENGTH: number = 400
const MAX_IDENTITY_BUSINESS_NAME_LENGTH: number = 120
const MAX_IDENTITY_PHONE_LENGTH: number = 32
const MAX_IDENTITY_CITY_LENGTH: number = 80
const MAX_IDENTITY_AREA_LENGTH: number = 120

/**
 * Validate and extract a template id from a raw message value.
 * @param raw - Untrusted `templateId` field of the message.
 * @returns The template id, or null when absent or invalid.
 */
function sanitizeTemplateId(raw: unknown): string | null {
  if (typeof raw !== 'string') return null
  const trimmed: string = raw.trim()
  return trimmed && trimmed.length <= MAX_TEMPLATE_ID_LENGTH ? trimmed : null
}

/**
 * Validate and extract a palette override from a raw message value.
 * @param raw - Untrusted `palette` field of the message.
 * @returns Only the known keys carrying a valid `#rrggbb` colour, or null when none survive.
 */
function sanitizePalette(raw: unknown): Record<string, string> | null {
  if (typeof raw !== 'object' || raw === null) return null
  const source: Record<string, unknown> = raw as Record<string, unknown>
  const palette: Record<string, string> = {}
  for (const key of PALETTE_KEYS) {
    const value: unknown = source[key]
    if (typeof value === 'string' && /^#[0-9A-Fa-f]{6}$/.test(value)) {
      palette[key] = value
    }
  }
  return Object.keys(palette).length > 0 ? palette : null
}

/**
 * Validate and extract a photo-order override from a raw message value.
 * @param raw - Untrusted `photos` field of the message.
 * @returns The photo URLs (https or data URIs), capped, or null when the field is not an array.
 */
function sanitizePhotos(raw: unknown): string[] | null {
  if (!Array.isArray(raw)) return null
  const photos: string[] = []
  for (const item of raw) {
    if (photos.length >= MAX_PHOTOS) break
    if (typeof item !== 'string' || item.length > MAX_PHOTO_LENGTH) continue
    if (/^(https?:\/\/|data:image\/)/.test(item)) photos.push(item)
  }
  return photos
}

/**
 * Validate and extract the curated section cards from a raw message value.
 * @param raw - Untrusted `services` field of the message.
 * @returns The cards with a non-empty title (texts capped, image an https/data URL or empty), or null when absent.
 */
function sanitizeServiceCards(raw: unknown): DemoPreviewServiceCard[] | null {
  if (!Array.isArray(raw)) return null
  const cards: DemoPreviewServiceCard[] = []
  for (const item of raw) {
    if (cards.length >= MAX_SERVICE_CARDS) break
    if (typeof item !== 'object' || item === null) continue
    const source: Record<string, unknown> = item as Record<string, unknown>
    const title: string = typeof source.title === 'string' ? source.title.trim().slice(0, MAX_SERVICE_TITLE_LENGTH) : ''
    if (!title) continue
    const description: string =
      typeof source.description === 'string' ? source.description.trim().slice(0, MAX_SERVICE_DESCRIPTION_LENGTH) : ''
    const rawImage: string = typeof source.image === 'string' ? source.image.trim() : ''
    const image: string =
      rawImage.length <= MAX_PHOTO_LENGTH && /^(https?:\/\/|data:image\/)/.test(rawImage) ? rawImage : ''
    cards.push({ title, description, image })
  }
  return cards
}

/**
 * Validate one single-line identity text.
 * @param raw - Untrusted field of the `identity` message object.
 * @param maxLength - Longest value kept.
 * @returns The trimmed text, control characters replaced by spaces, or null when absent, empty or too long.
 */
function sanitizeIdentityText(raw: unknown, maxLength: number): string | null {
  if (typeof raw !== 'string') {
    return null
  }
  const singleLine: string = raw.replace(/\p{Cc}+/gu, ' ').trim()
  return singleLine && singleLine.length <= maxLength ? singleLine : null
}

/**
 * Validate the logo of an identity message.
 * @param raw - Untrusted `logoUrl` field.
 * @returns The https or `data:image/` URL (at most the photo cap), or null.
 */
function sanitizeLogoUrl(raw: unknown): string | null {
  if (typeof raw !== 'string') {
    return null
  }
  const trimmed: string = raw.trim()
  return trimmed.length <= MAX_PHOTO_LENGTH && /^(https?:\/\/|data:image\/)/.test(trimmed) ? trimmed : null
}

/**
 * Validate and extract the business identity from a raw message value.
 * @param raw - Untrusted `identity` field of the message.
 * @returns The identity with each invalid field null, or null when absent or when no field survives.
 */
function sanitizeIdentity(raw: unknown): DemoPreviewIdentity | null {
  if (typeof raw !== 'object' || raw === null) {
    return null
  }
  const source: Record<string, unknown> = raw as Record<string, unknown>
  const identity: DemoPreviewIdentity = {
    businessName: sanitizeIdentityText(source.businessName, MAX_IDENTITY_BUSINESS_NAME_LENGTH),
    phone: sanitizeIdentityText(source.phone, MAX_IDENTITY_PHONE_LENGTH),
    city: sanitizeIdentityText(source.city, MAX_IDENTITY_CITY_LENGTH),
    area: sanitizeIdentityText(source.area, MAX_IDENTITY_AREA_LENGTH),
    logoUrl: sanitizeLogoUrl(source.logoUrl),
  }
  return Object.values(identity).some((value: string | null): boolean => value !== null) ? identity : null
}

/**
 * Listen for an embedder's live-edit messages and expose the current overrides.
 *
 * Origins are deliberately not filtered: the dashboard runs from several origins (Tauri shell,
 * web build, local dev), dibodev.fr frames the showroom demos, and a rogue embedder could only
 * restyle its OWN iframe — nothing is read back, persisted, or sent anywhere. The strict shape
 * validation above is the actual guard.
 * @param enabled - Whether live-edit mode is active (the `?_edit=1` query flag).
 * @returns The reactive overrides (all null until a first valid message arrives).
 */
export function useDemoPreviewOverrides(enabled: ComputedRef<boolean>): { overrides: Ref<DemoPreviewOverrides> } {
  const overrides: Ref<DemoPreviewOverrides> = ref<DemoPreviewOverrides>({
    templateId: null,
    palette: null,
    photos: null,
    services: null,
    identity: null,
  })

  /**
   * Apply one incoming `message` event when it carries a valid live-edit payload.
   * @param event - Raw message event from any parent window.
   */
  function onMessage(event: MessageEvent): void {
    if (!enabled.value) return
    const data: unknown = event.data
    if (typeof data !== 'object' || data === null) return
    const message: Record<string, unknown> = data as Record<string, unknown>
    if (message.type !== 'dlh:preview') return
    overrides.value = {
      templateId: sanitizeTemplateId(message.templateId),
      palette: sanitizePalette(message.palette),
      photos: sanitizePhotos(message.photos),
      services: sanitizeServiceCards(message.services),
      identity: sanitizeIdentity(message.identity),
    }
  }

  onMounted((): void => {
    window.addEventListener('message', onMessage)
  })

  onBeforeUnmount((): void => {
    window.removeEventListener('message', onMessage)
  })

  return { overrides }
}
