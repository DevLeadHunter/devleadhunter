<template>
  <div class="space-y-5">
    <section
      v-if="phase === 'permission'"
      class="flex flex-col items-center gap-5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-10 text-center"
    >
      <span
        class="flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)]"
      >
        <UIcon name="i-lucide-camera" class="h-5 w-5 text-[var(--app-ink)]" />
      </span>
      <div class="space-y-2">
        <h3 class="text-base font-semibold text-[var(--app-ink)]">On filme en trois fois, pas d'un coup</h3>
        <p class="text-muted mx-auto max-w-md text-sm leading-relaxed">
          Vous enregistrez l'intro, le milieu et la fin séparément, chacune reprenable autant de fois que vous voulez.
          Le texte à lire s'affiche à l'écran pendant que vous parlez.
        </p>
      </div>

      <UiCallout v-if="recorder.error.value" variant="warning" class="max-w-md text-left">
        {{ recorder.error.value }}
      </UiCallout>

      <button type="button" class="app-btn-primary" :disabled="recorder.isRequesting.value" @click="askForCamera">
        <UIcon
          :name="recorder.isRequesting.value ? 'i-lucide-loader-circle' : 'i-lucide-video'"
          :class="['h-3.5 w-3.5', recorder.isRequesting.value && 'animate-spin']"
        />
        {{ recorder.isRequesting.value ? 'Ouverture…' : 'Activer ma caméra' }}
      </button>
      <p class="text-muted text-xs">Rien n'est enregistré tant que vous n'avez pas lancé une prise.</p>
    </section>

    <template v-else>
      <ol class="grid grid-cols-3 gap-2">
        <li
          v-for="(segment, index) in script.segments.value"
          :key="segment.id"
          class="rounded-lg border px-3 py-2.5 transition-colors"
          :class="[
            index === currentIndex && phase !== 'ready'
              ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
              : 'border-[var(--app-line)] bg-[var(--app-surface)]',
          ]"
        >
          <div class="flex items-center gap-1.5">
            <UIcon v-if="keptTakes[index]" name="i-lucide-check" class="h-3.5 w-3.5 shrink-0 text-[var(--app-green)]" />
            <span v-else class="app-label shrink-0">{{ index + 1 }}</span>
            <p class="truncate text-xs font-semibold text-[var(--app-ink)]">{{ segment.title }}</p>
          </div>
          <p class="text-muted mt-0.5 text-[11px]">
            {{ keptTakes[index] ? formatSeconds(keptTakes[index]!.seconds) : `~${segment.targetSeconds} s` }}
          </p>
        </li>
      </ol>

      <div class="relative overflow-hidden rounded-xl border border-[var(--app-line)] bg-black">
        <video
          v-show="phase !== 'review'"
          ref="previewRef"
          autoplay
          muted
          playsinline
          class="aspect-video w-full -scale-x-100 object-cover"
        />
        <video
          v-if="phase === 'review' && pendingTake"
          :key="pendingTake.url"
          :src="pendingTake.url"
          controls
          autoplay
          playsinline
          class="aspect-video w-full object-cover"
        />

        <div
          v-if="showFramingGuide && phase !== 'review'"
          class="pointer-events-none absolute inset-0 flex items-center justify-center"
          aria-hidden="true"
        >
          <div class="aspect-square h-full rounded-full border-2 border-dashed border-white/70" />
        </div>

        <UiTeleprompter
          v-if="isFilming"
          variant="overlay"
          :text="currentSegment.text"
          :is-running="phase === 'recording'"
          :restart-token="restartToken"
        />

        <div
          v-if="phase === 'countdown'"
          class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/55"
        >
          <span class="text-6xl font-bold text-white tabular-nums">{{ countdown }}</span>
          <span class="text-sm font-medium text-white/80">Respirez…</span>
        </div>

        <div
          v-if="phase === 'recording'"
          class="absolute top-3 left-3 flex items-center gap-2 rounded-full bg-black/65 px-3 py-1.5"
        >
          <span class="h-2 w-2 animate-pulse rounded-full bg-[#e5484d]" aria-hidden="true" />
          <span class="text-xs font-semibold text-white tabular-nums">
            {{ formatSeconds(recorder.elapsedSeconds.value) }}
          </span>
          <span class="text-xs text-white/60">/ ~{{ currentSegment.targetSeconds }} s</span>
        </div>

        <span
          v-if="isWarmUp && isFilming"
          class="absolute top-3 right-3 rounded-full bg-[var(--app-accent)] px-2.5 py-1 text-[11px] font-semibold text-[#1b1508]"
        >
          Prise d'essai — non conservée
        </span>
      </div>

      <template v-if="phase === 'setup'">
        <UiCallout v-if="recorder.error.value" variant="warning">{{ recorder.error.value }}</UiCallout>

        <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5">
          <div class="flex items-start gap-3">
            <span class="app-badge shrink-0 font-medium">Prise {{ currentIndex + 1 }} / 3</span>
            <div class="min-w-0">
              <p class="text-sm font-semibold text-[var(--app-ink)]">{{ currentSegment.title }}</p>
              <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ currentSegment.staging }}</p>
            </div>
          </div>

          <div class="mt-4 space-y-2">
            <div class="flex items-center justify-between gap-3">
              <label class="app-label" :for="`script-${currentSegment.id}`">Votre texte</label>
              <button
                v-if="script.isCustomised.value"
                type="button"
                class="cursor-pointer text-[11px] font-medium text-[var(--app-ink-soft)] underline underline-offset-2 hover:text-[var(--app-ink)]"
                @click="script.resetToDefault()"
              >
                Revenir au texte conseillé
              </button>
            </div>
            <textarea
              :id="`script-${currentSegment.id}`"
              :value="currentSegment.text"
              rows="4"
              class="app-input h-auto min-h-24 w-full resize-y py-2 leading-relaxed"
              @input="onScriptInput"
            />
            <p class="text-muted text-[11px] leading-relaxed">
              Écrivez comme vous parlez : des phrases courtes, une idée par phrase. Ne nommez jamais une entreprise ni
              une section précise — ce clip sert pour tous vos prospects.
            </p>
          </div>
        </div>

        <UiCollapsibleCard icon="i-lucide-settings-2" title="Caméra, micro et cadrage" :default-open="!hasHeardSound">
          <div class="space-y-4 px-4 py-4">
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="app-label mb-1.5 block" for="recorder-camera">Caméra</label>
                <select
                  id="recorder-camera"
                  :value="recorder.selectedCameraId.value"
                  class="app-input"
                  @change="onCameraChange"
                >
                  <option v-for="device in recorder.cameras.value" :key="device.deviceId" :value="device.deviceId">
                    {{ device.label }}
                  </option>
                </select>
              </div>
              <div>
                <label class="app-label mb-1.5 block" for="recorder-microphone">Micro</label>
                <select
                  id="recorder-microphone"
                  :value="recorder.selectedMicrophoneId.value"
                  class="app-input"
                  @change="onMicrophoneChange"
                >
                  <option v-for="device in recorder.microphones.value" :key="device.deviceId" :value="device.deviceId">
                    {{ device.label }}
                  </option>
                </select>
              </div>
            </div>

            <div>
              <div class="mb-1.5 flex items-center justify-between gap-3">
                <span class="app-label">Niveau du micro</span>
                <span
                  class="text-[11px] font-medium"
                  :class="hasHeardSound ? 'text-[var(--app-green)]' : 'text-[var(--app-ink-soft)]'"
                >
                  {{ hasHeardSound ? 'Micro OK' : 'Dites quelque chose pour tester' }}
                </span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
                <div
                  class="h-full rounded-full transition-[width] duration-75"
                  :class="hasHeardSound ? 'bg-[var(--app-green)]' : 'bg-[var(--app-ink-soft)]'"
                  :style="{ width: `${Math.min(100, Math.round(recorder.audioLevel.value * 140))}%` }"
                />
              </div>
            </div>

            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <p class="text-sm font-medium text-[var(--app-ink)]">Voir le cadrage de la pastille</p>
                <p class="text-muted text-xs leading-relaxed">
                  Pendant la prise du milieu, vous apparaissez dans une pastille ronde : restez dans le cercle.
                </p>
              </div>
              <UiSwitch id="recorder-framing" v-model="showFramingGuide" />
            </div>

            <div class="flex flex-wrap gap-2">
              <span
                v-for="tip in RECORDING_TIPS"
                :key="tip"
                class="rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-1 text-xs text-[var(--app-ink)]"
              >
                {{ tip }}
              </span>
            </div>
          </div>
        </UiCollapsibleCard>

        <div class="flex flex-wrap items-center justify-between gap-3">
          <button type="button" class="app-btn-secondary" @click="startTake(true)">
            <UIcon name="i-lucide-flask-conical" class="h-3.5 w-3.5" />
            Prise d'essai
          </button>
          <div class="flex items-center gap-3">
            <button type="button" class="app-btn-secondary" @click="cancelRecording">Annuler</button>
            <button type="button" class="app-btn-primary" @click="startTake(false)">
              <span class="h-2.5 w-2.5 animate-pulse rounded-full bg-[#e5484d]" aria-hidden="true" />
              {{ keptTakes[currentIndex] ? 'Refaire cette prise' : `Filmer « ${currentSegment.title} »` }}
            </button>
          </div>
        </div>
        <p class="text-muted text-center text-xs">
          La prise d'essai n'est jamais conservée — elle sert juste à se lancer.
        </p>
      </template>

      <div v-else-if="isFilming" class="flex flex-col items-center gap-3">
        <div class="flex flex-wrap items-center justify-center gap-3">
          <button type="button" class="app-btn-secondary" :disabled="phase === 'countdown'" @click="restartTake">
            <UIcon name="i-lucide-rotate-ccw" class="h-3.5 w-3.5" />
            Réessayer
          </button>
          <button type="button" class="app-btn-primary px-6" :disabled="phase === 'countdown'" @click="finishTake">
            J'ai terminé
            <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
          </button>
        </div>
        <p class="text-muted text-xs">Ratée ? « Réessayer » relance la prise depuis le début.</p>
      </div>

      <template v-else-if="phase === 'review'">
        <UiCallout v-if="reviewWarning" variant="warning">{{ reviewWarning }}</UiCallout>
        <div class="flex flex-wrap items-center justify-center gap-3">
          <button type="button" class="app-btn-secondary" @click="retakeCurrent">
            <UIcon name="i-lucide-rotate-ccw" class="h-3.5 w-3.5" />
            Refaire
          </button>
          <button type="button" class="app-btn-primary" :disabled="Boolean(reviewWarning)" @click="keepCurrentTake">
            {{ currentIndex === script.segments.value.length - 1 ? 'Garder et terminer' : 'Garder et continuer' }}
            <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
          </button>
        </div>
      </template>

      <template v-else-if="phase === 'ready'">
        <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-4">
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-check-check" class="h-4 w-4 text-[var(--app-green)]" />
            <p class="text-sm font-semibold text-[var(--app-ink)]">
              Vos trois prises sont là — {{ formatSeconds(totalSeconds) }} au total
            </p>
          </div>
          <p class="text-muted mt-1.5 text-xs leading-relaxed">
            Elles sont assemblées à l'envoi. Les raccords tombent pile quand l'image change — au moment où le site
            apparaît, puis disparaît — donc ils ne se voient pas.
          </p>
        </div>

        <UiCallout v-if="assemblyWarning" variant="warning">{{ assemblyWarning }}</UiCallout>

        <div class="flex flex-wrap items-center justify-between gap-3">
          <button type="button" class="app-btn-secondary" :disabled="isSending" @click="restartAll">
            <UIcon name="i-lucide-rotate-ccw" class="h-3.5 w-3.5" />
            Tout recommencer
          </button>
          <div class="flex items-center gap-3">
            <button type="button" class="app-btn-secondary" :disabled="isSending" @click="cancelRecording">
              Annuler
            </button>
            <button
              type="button"
              class="app-btn-primary disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isSending || Boolean(assemblyWarning)"
              @click="sendTakes"
            >
              <UIcon
                :name="isSending ? 'i-lucide-loader-circle' : 'i-lucide-check'"
                :class="['h-3.5 w-3.5', isSending && 'animate-spin']"
              />
              {{ isSending ? 'Assemblage en cours…' : 'Enregistrer ma vidéo' }}
            </button>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { UseAuthReturn, UseToastReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { PresenterVideo } from '~/services/presenterVideoService'
import type { ProspectionScriptSegment } from '~/composables/useProspectionScript'
import type { RecordedTake } from '~/composables/useWebcamRecorder'
import type { KeptTake, RecorderPhase, UiPresenterVideoRecorderProps } from '~/types/UiPresenterVideoRecorder'
import { PresenterVideoService } from '~/services/presenterVideoService'
import { useAuth } from '~/composables/useAuth'
import { useProspectionScript } from '~/composables/useProspectionScript'
import { useToast } from '~/composables/useToast'
import { useWebcamRecorder } from '~/composables/useWebcamRecorder'

/** Three-take presenter recorder with on-screen teleprompter for montage cuts. */
const props: UiPresenterVideoRecorderProps = defineProps({
  autoGenerate: {
    type: Boolean,
    default: true,
  },
})

const emit: {
  /** The clip was assembled and stored — carries the fresh API payload. */
  (e: 'saved', info: PresenterVideo): void
  /** The user backed out of recording. */
  (e: 'cancel'): void
} = defineEmits<{
  /** The clip was assembled and stored — carries the fresh API payload. */
  (e: 'saved', info: PresenterVideo): void
  /** The user backed out of recording. */
  (e: 'cancel'): void
}>()

/** Short framing tips shown as pills next to the device pickers. */
const RECORDING_TIPS: string[] = ['Lumière face à vous', 'Caméra à hauteur des yeux', 'Pièce calme', 'Fond neutre']

/** Seconds counted down before the camera rolls. */
const COUNTDOWN_FROM: number = 3

/** Delay before the prompter starts, so the first word is never clipped. */
const LEAD_IN_MS: number = 600

/** Hard stop for a single take, mirroring the API's per-segment ceiling. */
const MAX_TAKE_SECONDS: number = 55

/** The middle take carries the site scroll; the montage refuses less than this. */
const MIN_MIDDLE_SECONDS: number = 6

/** Total clip bounds enforced by the API. */
const MIN_TOTAL_SECONDS: number = 12
const MAX_TOTAL_SECONDS: number = 90

const toast: UseToastReturn = useToast()
const { user }: UseAuthReturn = useAuth()
const recorder: ReturnType<typeof useWebcamRecorder> = useWebcamRecorder()
const script: {
  segments: Ref<ProspectionScriptSegment[], ProspectionScriptSegment[]>
  isCustomised: Ref<boolean, boolean>
  updateSegmentText: (id: ProspectionScriptSegmentId, text: string) => void
  resetToDefault: () => void
} = useProspectionScript(user.value?.name ?? '')

const phase: Ref<RecorderPhase> = ref('permission')
const currentIndex: Ref<number> = ref(0)
const keptTakes: Ref<Array<KeptTake | null>> = ref([null, null, null])
const pendingTake: Ref<RecordedTake | null> = ref(null)
const previewRef: Ref<HTMLVideoElement | null> = ref(null)
const countdown: Ref<number> = ref(COUNTDOWN_FROM)
const isWarmUp: Ref<boolean> = ref(false)
const isSending: Ref<boolean> = ref(false)
const showFramingGuide: Ref<boolean> = ref(false)
const hasHeardSound: Ref<boolean> = ref(false)
const restartToken: Ref<number> = ref(0)

/** Pending timers, cleared whenever the flow is interrupted. */
let countdownHandle: ReturnType<typeof setInterval> | null = null
let leadInHandle: ReturnType<typeof setTimeout> | null = null

/** The take being filmed or about to be. */
const currentSegment: ComputedRef<ProspectionScriptSegment> = computed((): ProspectionScriptSegment => {
  const segments: ProspectionScriptSegment[] = script.segments.value
  return segments[currentIndex.value] ?? segments[0]!
})

/** Whether the camera is rolling (or about to). */
const isFilming: ComputedRef<boolean> = computed(
  (): boolean => phase.value === 'countdown' || phase.value === 'recording',
)

/** Total length of the takes kept so far. */
const totalSeconds: ComputedRef<number> = computed((): number =>
  keptTakes.value.reduce((sum: number, kept: KeptTake | null): number => sum + (kept?.seconds ?? 0), 0),
)

/** Why the take under review cannot be kept, when it cannot. */
const reviewWarning: ComputedRef<string> = computed((): string => {
  const take: RecordedTake | null = pendingTake.value
  if (!take) return ''
  if (take.durationSeconds < 1) return 'Cette prise est trop courte pour être exploitable — refaites-la.'
  if (currentIndex.value === 1 && take.durationSeconds < MIN_MIDDLE_SECONDS) {
    return (
      `Cette prise ne dure que ${formatSeconds(take.durationSeconds)} : c'est elle qui couvre le défilement du ` +
      `site, il lui faut au moins ${MIN_MIDDLE_SECONDS} secondes.`
    )
  }
  return ''
})

/** Why the three takes cannot be assembled, when they cannot. */
const assemblyWarning: ComputedRef<string> = computed((): string => {
  const total: number = totalSeconds.value
  if (total < MIN_TOTAL_SECONDS) {
    return `Vos trois prises ne font que ${formatSeconds(total)} — il en faut au moins ${MIN_TOTAL_SECONDS}.`
  }
  if (total > MAX_TOTAL_SECONDS) {
    return `Vos trois prises font ${formatSeconds(total)} — c'est trop long, la limite est de ${MAX_TOTAL_SECONDS} secondes.`
  }
  return ''
})

/**
 * Format a duration for display.
 * @param seconds - Raw duration.
 * @returns A short French label (e.g. « 24 s »).
 */
function formatSeconds(seconds: number): string {
  return `${Math.round(seconds)} s`
}

/** Cancel the countdown and lead-in timers. */
function clearTimers(): void {
  if (countdownHandle !== null) {
    clearInterval(countdownHandle)
    countdownHandle = null
  }
  if (leadInHandle !== null) {
    clearTimeout(leadInHandle)
    leadInHandle = null
  }
}

/** Bind the live stream to the preview element (re-run whenever either changes). */
async function bindPreview(): Promise<void> {
  await nextTick()
  const element: HTMLVideoElement | null = previewRef.value
  if (element && element.srcObject !== recorder.stream.value) {
    element.srcObject = recorder.stream.value
  }
}

/** Ask for camera access, then open the studio. */
async function askForCamera(): Promise<void> {
  const granted: boolean = await recorder.requestAccess()
  if (!granted) return
  phase.value = 'setup'
  await bindPreview()
}

/**
 * Reopen the stream on the picked camera.
 * @param event - Change event of the camera select.
 */
async function onCameraChange(event: Event): Promise<void> {
  const value: string = (event.target as HTMLSelectElement).value
  await recorder.switchDevices(value, recorder.selectedMicrophoneId.value)
  await bindPreview()
}

/**
 * Reopen the stream on the picked microphone.
 * @param event - Change event of the microphone select.
 */
async function onMicrophoneChange(event: Event): Promise<void> {
  const value: string = (event.target as HTMLSelectElement).value
  hasHeardSound.value = false
  await recorder.switchDevices(recorder.selectedCameraId.value, value)
  await bindPreview()
}

/**
 * Save an edit of the current take's script.
 * @param event - Input event of the textarea.
 */
function onScriptInput(event: Event): void {
  script.updateSegmentText(currentSegment.value.id, (event.target as HTMLTextAreaElement).value)
}

/**
 * Roll the countdown, then start recording.
 * @param warmUp - True for a throwaway take that is never kept.
 */
function startTake(warmUp: boolean): void {
  if (!recorder.isReady.value) return
  isWarmUp.value = warmUp
  countdown.value = COUNTDOWN_FROM
  phase.value = 'countdown'

  clearTimers()
  countdownHandle = setInterval((): void => {
    countdown.value -= 1
    if (countdown.value > 0) return

    clearTimers()
    if (!recorder.startRecording()) {
      phase.value = 'setup'
      return
    }
    phase.value = 'recording'
    // Le prompteur démarre après la capture, sinon la première syllabe est rognée.
    restartToken.value += 1
    leadInHandle = setTimeout((): void => {
      restartToken.value += 1
    }, LEAD_IN_MS)
  }, 1000)
}

/** Stop the take and move to its review (or drop it when it was a warm-up). */
async function finishTake(): Promise<void> {
  clearTimers()
  const take: RecordedTake | null = await recorder.stopRecording()
  if (!take) {
    phase.value = 'setup'
    return
  }
  if (isWarmUp.value) {
    recorder.releaseTake(take)
    isWarmUp.value = false
    phase.value = 'setup'
    toast.success('Prise d’essai terminée — elle n’a pas été conservée')
    await bindPreview()
    return
  }
  pendingTake.value = take
  phase.value = 'review'
}

/** Restart the current take from the countdown without entering review. */
async function restartTake(): Promise<void> {
  const wasWarmUp: boolean = isWarmUp.value
  clearTimers()
  if (recorder.isRecording.value) {
    const take: RecordedTake | null = await recorder.stopRecording()
    if (take) recorder.releaseTake(take)
  }
  startTake(wasWarmUp)
}

/** Keep the reviewed take and go to the next one (or to the recap). */
async function keepCurrentTake(): Promise<void> {
  const take: RecordedTake | null = pendingTake.value
  if (!take || reviewWarning.value) return

  const previous: KeptTake | null = keptTakes.value[currentIndex.value] ?? null
  if (previous) recorder.releaseTake(previous.take)

  const next: Array<KeptTake | null> = [...keptTakes.value]
  next[currentIndex.value] = { take, seconds: take.durationSeconds }
  keptTakes.value = next
  pendingTake.value = null

  const nextMissing: number = next.findIndex((kept: KeptTake | null): boolean => kept === null)
  if (nextMissing === -1) {
    phase.value = 'ready'
  } else {
    currentIndex.value = nextMissing
    phase.value = 'setup'
  }
  await bindPreview()
}

/** Drop the reviewed take and film it again. */
async function retakeCurrent(): Promise<void> {
  if (pendingTake.value) recorder.releaseTake(pendingTake.value)
  pendingTake.value = null
  phase.value = 'setup'
  await bindPreview()
}

/** Forget every take and start over from the first one. */
async function restartAll(): Promise<void> {
  keptTakes.value.forEach((kept: KeptTake | null): void => {
    if (kept) recorder.releaseTake(kept.take)
  })
  keptTakes.value = [null, null, null]
  currentIndex.value = 0
  phase.value = 'setup'
  await bindPreview()
}

/** Release every object URL held by the component. */
function releaseAllTakes(): void {
  keptTakes.value.forEach((kept: KeptTake | null): void => {
    if (kept) recorder.releaseTake(kept.take)
  })
  keptTakes.value = [null, null, null]
  if (pendingTake.value) recorder.releaseTake(pendingTake.value)
  pendingTake.value = null
}

/** Close the camera and leave the recorder. */
function cancelRecording(): void {
  clearTimers()
  releaseAllTakes()
  recorder.stopEverything()
  emit('cancel')
}

/** Send the three takes; the API concatenates and measures them. */
async function sendTakes(): Promise<void> {
  const takes: KeptTake[] = keptTakes.value.filter((kept: KeptTake | null): kept is KeptTake => kept !== null)
  if (takes.length !== script.segments.value.length || assemblyWarning.value) return

  isSending.value = true
  try {
    const [intro, middle, outro]: File[] = takes.map(
      (kept: KeptTake, index: number): File =>
        new File([kept.take.blob], `${['intro', 'middle', 'outro'][index]}.${kept.take.extension}`, {
          type: kept.take.blob.type,
        }),
    )
    const info: PresenterVideo = await PresenterVideoService.uploadPresenterVideoSegments(
      intro!,
      middle!,
      outro!,
      props.autoGenerate,
    )
    releaseAllTakes()
    recorder.stopEverything()
    toast.success('Votre vidéo est prête — les prochains sites démo l’utiliseront automatiquement')
    emit('saved', info)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'assemblage")
  } finally {
    isSending.value = false
  }
}

// Un micro qui a « fait du bruit » au moins une fois est un micro branché.
watch(
  (): number => recorder.audioLevel.value,
  (level: number): void => {
    if (level > 0.06) hasHeardSound.value = true
  },
)

// Filet de sécurité : une prise oubliée ne dépasse pas la limite de l'API.
watch(
  (): number => recorder.elapsedSeconds.value,
  (elapsed: number): void => {
    if (phase.value === 'recording' && elapsed >= MAX_TAKE_SECONDS) void finishTake()
  },
)

watch(
  (): MediaStream | null => recorder.stream.value,
  (): void => {
    void bindPreview()
  },
)

onBeforeUnmount((): void => {
  clearTimers()
  releaseAllTakes()
})
</script>
