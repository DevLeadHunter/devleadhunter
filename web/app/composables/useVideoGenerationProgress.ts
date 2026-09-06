/**
 * Live progress of a desktop video build, for the generation modal.
 *
 * Polls the sidecar's per-slug phase while a build runs, turns it into a step
 * list + a timestamped log, and lets the caller drive the outcome (finish/fail).
 * @module composables/useVideoGenerationProgress
 */

import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, ref } from 'vue'
import type { VideoGenerationStep, VideoGenerationStepState } from '~/types/UiVideoGenerationModal'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'

/** Ordered sidecar phases; the final step (publication/preview) is app-driven. */
const SIDECAR_STEP_ORDER: string[] = ['preparing', 'site_capture', 'editor_capture', 'background_assemble', 'montage']

/** Step labels shown in the modal (the sidecar messages feed the log lines). */
const STEP_LABELS: Record<string, string> = {
  preparing: 'Préparation (contexte + clip présentateur)',
  site_capture: 'Capture du site (défilement)',
  editor_capture: 'Séquence éditeur Storyblok',
  background_assemble: 'Assemblage du fond',
  montage: 'Montage final (webcam + habillage)',
}

/** How often the sidecar phase is polled while a build runs. */
const PROGRESS_POLL_MS: number = 1500

export type UseVideoGenerationProgressReturn = {
  isOpen: Ref<boolean>
  isRunning: Ref<boolean>
  steps: ComputedRef<VideoGenerationStep[]>
  logLines: Ref<string[]>
  elapsedSeconds: Ref<number>
  errorMessage: Ref<string>
  start: (slug: string, finalStepLabel: string) => void
  note: (message: string) => void
  finish: () => void
  fail: (message: string) => void
  close: () => void
}

/**
 * Progress state + controls for the video-generation modal.
 * @returns Reactive modal state and its lifecycle controls.
 */
export function useVideoGenerationProgress(): UseVideoGenerationProgressReturn {
  const isOpen: Ref<boolean> = ref(false)
  const isRunning: Ref<boolean> = ref(false)
  const logLines: Ref<string[]> = ref([])
  const elapsedSeconds: Ref<number> = ref(0)
  const errorMessage: Ref<string> = ref('')
  const currentStepKey: Ref<string> = ref('preparing')
  const finalStepLabel: Ref<string> = ref('Publication de la vidéo')
  const hasFailed: Ref<boolean> = ref(false)
  const hasCompleted: Ref<boolean> = ref(false)

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let clockTimer: ReturnType<typeof setInterval> | null = null
  let startedAtMs: number = 0
  let lastLoggedStep: string = ''

  const steps: ComputedRef<VideoGenerationStep[]> = computed((): VideoGenerationStep[] => {
    const keys: string[] = [...SIDECAR_STEP_ORDER, 'finalize']
    const activeIndex: number = keys.indexOf(currentStepKey.value)
    return keys.map((key: string, index: number): VideoGenerationStep => {
      const label: string = key === 'finalize' ? finalStepLabel.value : (STEP_LABELS[key] ?? key)
      let state: VideoGenerationStepState = 'pending'
      if (hasCompleted.value || index < activeIndex) state = 'done'
      else if (index === activeIndex) state = hasFailed.value ? 'error' : 'active'
      return { key, label, state }
    })
  })

  /**
   * Append a timestamped line to the modal's log.
   * @param message - What just happened.
   */
  function appendLog(message: string): void {
    const minutes: number = Math.floor(elapsedSeconds.value / 60)
    const seconds: number = elapsedSeconds.value % 60
    logLines.value = [...logLines.value, `[${minutes}:${String(seconds).padStart(2, '0')}] ${message}`]
  }

  /** Stop the poll + clock timers. */
  function stopTimers(): void {
    if (pollTimer !== null) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (clockTimer !== null) {
      clearInterval(clockTimer)
      clockTimer = null
    }
  }

  /**
   * Open the modal and start following a build.
   * @param slug - Slug of the demo site being rendered (the sidecar's progress key).
   * @param finalLabel - Label of the last, app-driven step (publish vs preview).
   */
  function start(slug: string, finalLabel: string): void {
    stopTimers()
    isOpen.value = true
    isRunning.value = true
    hasFailed.value = false
    hasCompleted.value = false
    errorMessage.value = ''
    logLines.value = []
    elapsedSeconds.value = 0
    currentStepKey.value = 'preparing'
    finalStepLabel.value = finalLabel
    lastLoggedStep = ''
    startedAtMs = Date.now()
    appendLog('Démarrage de la génération…')

    clockTimer = setInterval((): void => {
      elapsedSeconds.value = Math.round((Date.now() - startedAtMs) / 1000)
    }, 1000)
    pollTimer = setInterval(async (): Promise<void> => {
      const progress: Awaited<ReturnType<typeof StoryblokSidecarService.getVideoBuildProgress>> =
        await StoryblokSidecarService.getVideoBuildProgress(slug)
      if (!progress || !isRunning.value) return
      // Ignore the previous build's leftover entry (the new one overwrites it within seconds).
      if (progress.updatedAt * 1000 < startedAtMs - 2000) return
      if (progress.step === 'error') return // the caller decides (fail / server fallback)
      const key: string = progress.step === 'done' ? 'finalize' : progress.step
      if (SIDECAR_STEP_ORDER.includes(key) || key === 'finalize') currentStepKey.value = key
      if (progress.step !== lastLoggedStep && progress.message) {
        lastLoggedStep = progress.step
        appendLog(progress.message)
      }
    }, PROGRESS_POLL_MS)
  }

  /**
   * Append an app-side event to the log (fallback, retry, upload…).
   * @param message - What just happened.
   */
  function note(message: string): void {
    appendLog(message)
  }

  /** Mark the build successful: every step turns done and the timers stop. */
  function finish(): void {
    stopTimers()
    isRunning.value = false
    hasCompleted.value = true
    appendLog('Terminé ✓')
  }

  /**
   * Mark the build failed: the active step turns red and the message is shown.
   * @param message - The failure, in the user's terms.
   */
  function fail(message: string): void {
    stopTimers()
    isRunning.value = false
    hasFailed.value = true
    errorMessage.value = message
    appendLog(`Échec : ${message}`)
  }

  /** Hide the modal (a still-running build keeps going in the background). */
  function close(): void {
    stopTimers()
    isRunning.value = false
    isOpen.value = false
  }

  onBeforeUnmount((): void => {
    stopTimers()
  })

  return { isOpen, isRunning, steps, logLines, elapsedSeconds, errorMessage, start, note, finish, fail, close }
}
