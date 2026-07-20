/**
 * Composable owning the spoken script read while recording the presenter clip.
 * @module composables/useProspectionScript
 */

import type { Ref } from 'vue'
import { ref } from 'vue'

/** The three takes, in the order they are filmed and played. */
export type ProspectionScriptSegmentId = 'intro' | 'middle' | 'outro'

/** One take: what is on screen, how long it should run, and what to say. */
export interface ProspectionScriptSegment {
  id: ProspectionScriptSegmentId
  /** Short name shown on the stepper and on the take card. */
  title: string
  /** What the prospect sees during this take — it sets the delivery. */
  staging: string
  /** Suggested length in seconds. Guidance for the timer, never a cut-off. */
  targetSeconds: number
  /** The words to read out loud. */
  text: string
}

/** localStorage key holding the user's edited script. */
const SCRIPT_STORAGE_KEY = 'dlh-prospection-script'

/**
 * Default script, written to be *spoken*: short sentences, one idea each, no
 * subordinate clauses. A paragraph that reads well on screen collapses when
 * read aloud by someone who is already uncomfortable being filmed.
 *
 * It stays 100 % generic — one recording is reused for every prospect, so it
 * must never name a company or describe a specific section of the site.
 *
 * @param presenterName - The connected user's name, woven into the greeting.
 * @returns The three default takes.
 */
export function buildDefaultScript(presenterName: string): ProspectionScriptSegment[] {
  const name: string = presenterName.trim()
  return [
    {
      id: 'intro',
      title: 'Intro',
      staging: 'Vous, en plein écran. Le prénom du prospect s’affiche à côté de vous.',
      targetSeconds: 5,
      text: name
        ? `Bonjour ! Moi c'est ${name}, développeur web. Trente secondes, pas plus, et vous allez comprendre pourquoi je vous écris.`
        : 'Bonjour ! Je suis développeur web. Trente secondes, pas plus, et vous allez comprendre pourquoi je vous écris.',
    },
    {
      id: 'middle',
      title: 'Le site apparaît',
      staging: 'Son site défile à l’écran. Vous passez en petite pastille ronde, en bas à gauche.',
      targetSeconds: 25,
      text:
        "Si je vous contacte, c'est que je vous ai déjà créé un site. " +
        'Celui que vous voyez là, c’est le vôtre. ' +
        'Il est déjà en ligne, à votre nom, avec vos vraies informations. ' +
        'Et surtout, vous pouvez tout changer vous-même. ' +
        'Les textes, les photos, les horaires. ' +
        'Sans développeur, et sans rien y connaître.',
    },
    {
      id: 'outro',
      title: 'Outro',
      staging: 'Retour sur vous en plein écran, pour l’appel à l’action.',
      targetSeconds: 6,
      text: 'Le lien est juste en dessous. Jetez-y un œil, ça vaut vraiment le coup. À tout de suite !',
    },
  ]
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
 * The editable prospection script, persisted on this machine.
 *
 * Kept in ``localStorage`` rather than in the database on purpose: it is an
 * authoring aid, not product data — the artefact that matters (the recorded
 * clip) is stored server-side, and the defaults are good enough that losing
 * an edit costs nothing.
 *
 * @param presenterName - The connected user's name, used to seed the defaults.
 * @returns The script plus its edit helpers.
 */
export function useProspectionScript(presenterName: string): {
  segments: Ref<ProspectionScriptSegment[]>
  isCustomised: Ref<boolean>
  updateSegmentText: (id: ProspectionScriptSegmentId, text: string) => void
  resetToDefault: () => void
} {
  const defaults: ProspectionScriptSegment[] = buildDefaultScript(presenterName)
  const segments: Ref<ProspectionScriptSegment[]> = ref<ProspectionScriptSegment[]>(defaults)
  const isCustomised: Ref<boolean> = ref<boolean>(false)

  /** Persist the current texts (only the texts — the staging is app-owned). */
  function persist(): void {
    if (!import.meta.client) return
    const payload: Record<string, string> = {}
    for (const segment of segments.value) payload[segment.id] = segment.text
    localStorage.setItem(SCRIPT_STORAGE_KEY, JSON.stringify(payload))
  }

  /** Restore the saved texts over the defaults, ignoring anything malformed. */
  function restore(): void {
    if (!import.meta.client) return
    const raw: string | null = localStorage.getItem(SCRIPT_STORAGE_KEY)
    if (!raw) return
    try {
      const parsed: unknown = JSON.parse(raw)
      if (typeof parsed !== 'object' || parsed === null) return
      const saved = parsed as Record<string, unknown>
      let touched: boolean = false
      segments.value = segments.value.map((segment: ProspectionScriptSegment): ProspectionScriptSegment => {
        const text: unknown = saved[segment.id]
        if (typeof text !== 'string' || text.trim().length === 0) return segment
        if (text !== segment.text) touched = true
        return { ...segment, text }
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

  /** Drop the edits and go back to the recommended script. */
  function resetToDefault(): void {
    segments.value = buildDefaultScript(presenterName)
    isCustomised.value = false
    if (import.meta.client) localStorage.removeItem(SCRIPT_STORAGE_KEY)
  }

  restore()

  return { segments, isCustomised, updateSegmentText, resetToDefault }
}
