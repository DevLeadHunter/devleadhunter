/**
 * Composable owning the spoken script read while recording the presenter clip.
 * @module composables/useProspectionScript
 */

import type { Ref } from 'vue'
import type { ProductModuleKey } from '~/types/ProductModule'
import type { PresenterVideoModuleAdapter } from '~/types/PresenterVideoConfig'
import { ref } from 'vue'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { PresenterVideoAdapterRegistry } from '~/utils/presenterVideoAdapterRegistry'

/** The three takes, in the order they are filmed and played. */
export type ProspectionScriptSegmentId = 'intro' | 'middle' | 'outro'

/** The sellable module a presenter clip belongs to: its takes describe what the montage shows. */
export type ProspectionScriptModule = ProductModuleKey

/** One take: what is on screen, how long it should run, and what to say. */
export type ProspectionScriptSegment = {
  id: ProspectionScriptSegmentId
  title: string
  staging: string
  targetSeconds: number
  text: string
}

/** One edited take as saved on this machine, with the recommended text it was written from. */
export type ProspectionScriptSavedSegment = {
  text: string
  defaultText: string
}

/** localStorage key holding the user's edited script of the websites clip (each module adapter names its own). */
export const WEBSITES_SCRIPT_STORAGE_KEY: string = 'dlh-prospection-script'

/**
 * Default spoken script: generic (never names the prospect) and, for the middle take, in the fixed order of the rendered background — the site scrolls, then the Storyblok editor appears.
 * @param presenterName - The connected user's full name, woven into the greeting.
 * @param companyName - The user's optional business name, appended to the greeting when set.
 * @returns The three default takes.
 */
export function buildDefaultScript(presenterName: string, companyName: string): ProspectionScriptSegment[] {
  const name: string = presenterName.trim()
  const company: string = companyName.trim()
  const presenter: string = company ? `${name} de ${company}` : name
  return [
    {
      id: 'intro',
      title: 'Intro',
      staging: 'Vous, en plein écran. Le prénom du prospect s’affiche à côté de vous.',
      targetSeconds: 6,
      text: name
        ? `Bonjour, moi c'est ${presenter}, je suis développeur web à Rennes.`
        : 'Bonjour, je suis développeur web à Rennes.',
    },
    {
      id: 'middle',
      title: 'Le site, puis l’espace d’administration',
      staging:
        'Son site défile pendant les premières secondes, puis son espace d’administration apparaît à l’écran. ' +
        'Vous passez en petite pastille ronde, en bas à gauche.',
      targetSeconds: 29,
      text:
        'Je me suis permis de vous créer votre site internet, celui que vous avez actuellement sous les yeux. ' +
        'Il est déjà en ligne, avec vos photos, vos horaires, vos coordonnées. ' +
        "Et ça, c'est votre espace d'administration. " +
        "C'est là que vous gérez tout vous-même : vous changez un texte, une photo, vous ajoutez une page. " +
        'Pas besoin de développeur, pas besoin de moi.',
    },
    {
      id: 'outro',
      title: 'Outro',
      staging: 'Retour sur vous en plein écran, pour l’appel à l’action.',
      targetSeconds: 13,
      text:
        'Le lien pour voir votre site par vous-même est juste en dessous de la vidéo. ' +
        "N'hésitez pas à y jeter un coup d'œil, et dites-moi ce que vous en pensez. Bonne journée !",
    },
  ]
}

/**
 * The default takes of a module's clip.
 * @param module - The sellable module the clip belongs to.
 * @param presenterName - The connected user's full name.
 * @param companyName - The user's optional business name.
 * @returns The three default takes.
 */
export function buildScriptFor(
  module: ProspectionScriptModule,
  presenterName: string,
  companyName: string,
): ProspectionScriptSegment[] {
  const adapter: PresenterVideoModuleAdapter | null = PresenterVideoAdapterRegistry.of(module)
  return adapter
    ? adapter.buildDefaultScript(presenterName, companyName)
    : buildDefaultScript(presenterName, companyName)
}

/**
 * Cut a take into the short beats the teleprompter highlights one by one.
 *
 * Splitting on sentence endings is what keeps each highlighted line to a few
 * words: a narrow line is read with barely a glance, where a wide paragraph
 * makes the eyes sweep visibly.
 *
 * @param text - The full text of one take.
 * @returns Its sentences, trimmed, without empties.
 */
export function splitIntoBeats(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+/u)
    .map((beat: string): string => beat.trim())
    .filter((beat: string): boolean => beat.length > 0)
}

/**
 * Roughly how long a beat takes to say, used to advance the highlight on its own.
 * @param beat - One sentence of the script.
 * @returns Seconds, floored so a three-word line never flashes past.
 */
export function estimateBeatSeconds(beat: string): number {
  const words: number = beat.split(/\s+/u).filter(Boolean).length
  // ~2.3 words per second is an unhurried spoken pace.
  return Math.max(1.6, words / 2.3)
}

/**
 * Whether a stored entry has the saved-segment shape.
 * @param entry - A value read back from localStorage.
 * @returns True for `{ text, defaultText }`; entries written before that shape existed fail and fall back to the default.
 */
function isSavedSegment(entry: unknown): entry is ProspectionScriptSavedSegment {
  if (typeof entry !== 'object' || entry === null) return false
  return (
    'text' in entry && typeof entry.text === 'string' && 'defaultText' in entry && typeof entry.defaultText === 'string'
  )
}

/**
 * The editable prospection script, persisted on this machine.
 *
 * Kept in ``localStorage`` rather than in the database on purpose: it is an
 * authoring aid, not product data — the artefact that matters (the recorded
 * clip) is stored server-side, and the defaults are good enough that losing
 * an edit costs nothing.
 *
 * @param presenterName - The connected user's full name, used to seed the defaults.
 * @param companyName - The user's optional business name, used to seed the defaults.
 * @param module - The sellable module the clip belongs to (the site clip by default).
 * @returns The script plus its edit helpers.
 */
export function useProspectionScript(
  presenterName: string,
  companyName: string,
  module: ProspectionScriptModule = WEBSITES_MODULE_KEY,
): {
  segments: Ref<ProspectionScriptSegment[]>
  isCustomised: Ref<boolean>
  updateSegmentText: (id: ProspectionScriptSegmentId, text: string) => void
  resetToDefault: () => void
} {
  const defaults: ProspectionScriptSegment[] = buildScriptFor(module, presenterName, companyName)
  const storageKey: string =
    PresenterVideoAdapterRegistry.of(module)?.scriptStorageKey ?? `${WEBSITES_SCRIPT_STORAGE_KEY}-${module}`
  const segments: Ref<ProspectionScriptSegment[]> = ref(defaults)
  const isCustomised: Ref<boolean> = ref(false)

  /**
   * The recommended text of one take, which an edit is checked against on restore.
   * @param id - Which take.
   * @returns Its default text.
   */
  function defaultTextOf(id: ProspectionScriptSegmentId): string {
    return defaults.find((segment: ProspectionScriptSegment): boolean => segment.id === id)?.text ?? ''
  }

  /** Persist the current texts with the default each was written from (the staging is app-owned). */
  function persist(): void {
    if (!import.meta.client) return
    const payload: Record<string, ProspectionScriptSavedSegment> = {}
    for (const segment of segments.value) {
      payload[segment.id] = { text: segment.text, defaultText: defaultTextOf(segment.id) }
    }
    localStorage.setItem(storageKey, JSON.stringify(payload))
  }

  /** Restore the saved texts over the defaults; an edit of a default that has since changed is dropped. */
  function restore(): void {
    if (!import.meta.client) return
    const raw: string | null = localStorage.getItem(storageKey)
    if (!raw) return
    try {
      const parsed: unknown = JSON.parse(raw)
      if (typeof parsed !== 'object' || parsed === null) return
      const saved: Record<string, unknown> = parsed as Record<string, unknown>
      let touched: boolean = false
      segments.value = segments.value.map((segment: ProspectionScriptSegment): ProspectionScriptSegment => {
        const entry: unknown = saved[segment.id]
        if (!isSavedSegment(entry) || entry.defaultText !== segment.text) return segment
        if (entry.text.trim().length === 0) return segment
        if (entry.text !== segment.text) touched = true
        return { ...segment, text: entry.text }
      })
      isCustomised.value = touched
    } catch {
      // A corrupted entry just means « use the defaults ».
    }
  }

  /**
   * Replace one take's text and save.
   * @param id - Which take to edit.
   * @param text - Its new content.
   */
  function updateSegmentText(id: ProspectionScriptSegmentId, text: string): void {
    segments.value = segments.value.map(
      (segment: ProspectionScriptSegment): ProspectionScriptSegment =>
        segment.id === id ? { ...segment, text } : segment,
    )
    isCustomised.value = true
    persist()
  }

  /** Drop the edits and go back to the recommended script of this clip's module. */
  function resetToDefault(): void {
    segments.value = buildScriptFor(module, presenterName, companyName)
    isCustomised.value = false
    if (import.meta.client) localStorage.removeItem(storageKey)
  }

  restore()

  return { segments, isCustomised, updateSegmentText, resetToDefault }
}
