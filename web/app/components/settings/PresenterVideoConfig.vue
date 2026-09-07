<template>
  <div class="space-y-8">
    <UiLoader v-if="isLoading" />

    <template v-else>
      <section class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Votre clip</h2>
          <span v-if="isClipFileMissing" class="app-badge app-badge--danger font-medium">
            <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5" />
            Fichier introuvable
          </span>
          <span v-else-if="info?.has_video" class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Prêt
          </span>
        </div>

        <UiCallout v-if="isClipFileMissing" variant="danger">
          Un clip est enregistré mais son fichier est introuvable sur le stockage — les vidéos de prospection ne peuvent
          pas être générées. Refilmez ou réimportez un clip pour repartir.
        </UiCallout>
        <div v-if="showClipPlayer" class="space-y-3">
          <div class="relative">
            <video
              :src="previewUrl ?? undefined"
              controls
              playsinline
              preload="auto"
              class="aspect-video w-full rounded-xl border border-[var(--app-line)] bg-black"
              @loadeddata="revealFirstFrame"
            />
            <button
              type="button"
              class="btn-danger absolute top-3 right-3 z-10 flex h-8 min-h-8 items-center justify-center px-2.5 text-xs disabled:opacity-50"
              :disabled="isDeleting"
              aria-label="Supprimer le clip"
              title="Supprimer le clip"
              @click="askDeleteClip"
            >
              <UIcon
                :name="isDeleting ? 'i-lucide-loader-circle' : 'i-lucide-x'"
                :class="['h-3.5 w-3.5', isDeleting && 'animate-spin']"
              />
            </button>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--app-ink-soft)]">
              <span v-if="clipDurationLabel" class="font-label text-[var(--app-ink)]">{{ clipDurationLabel }}</span>
              <span v-if="clipDurationLabel && info?.original_filename" aria-hidden="true">·</span>
              <span v-if="info?.original_filename" class="truncate">{{ info.original_filename }}</span>
              <span aria-hidden="true">·</span>
              <span>{{ isRecordedClip ? 'Filmé dans l’application' : 'Fichier importé' }}</span>
            </p>
            <button type="button" class="app-btn-secondary h-8 px-3 text-xs" @click="startClipReplacement">
              <UIcon name="i-lucide-refresh-cw" class="h-3.5 w-3.5" />
              Remplacer le clip
            </button>
          </div>
        </div>
        <template v-else>
          <button
            v-if="isReplacingClip && captureMode === null"
            type="button"
            class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
            @click="isReplacingClip = false"
          >
            Garder le clip actuel
          </button>
          <div v-if="captureMode === null" class="grid gap-3 sm:grid-cols-2">
            <button
              v-for="option in CAPTURE_OPTIONS"
              :key="option.mode"
              type="button"
              class="flex cursor-pointer flex-col items-start gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-4 text-left transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]"
              @click="captureMode = option.mode"
            >
              <span
                class="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
              >
                <UIcon :name="option.icon" class="h-4 w-4 text-[var(--app-ink)]" />
              </span>
              <span class="text-sm font-semibold text-[var(--app-ink)]">{{ option.title }}</span>
              <span class="text-muted text-xs leading-relaxed">{{ option.detail }}</span>
              <span v-if="option.badge" class="app-badge app-badge--info mt-1 font-medium">{{ option.badge }}</span>
            </button>
          </div>
          <UiPresenterVideoRecorder
            v-else-if="captureMode === 'record'"
            :auto-generate="autoGenerate"
            @saved="handleRecorded"
            @cancel="captureMode = null"
          />
          <div v-else class="space-y-3">
            <UiPresenterVideoDropzone
              :selected-file="selectedFile"
              :is-dragging="isDragging"
              :is-uploading="isUploading"
              :picked-clip-preview-url="pickedClipPreviewUrl"
              :is-compressing="isCompressing"
              :compression-progress="compressionProgress"
              :bytes-before-compression="pickedClipOriginalBytes"
              :size-error-message="clipSizeErrorMessage"
              @pick="openFilePicker"
              @drop-file="handleDropFile"
              @dragging="isDragging = $event"
              @upload="handleUpload"
            />
            <button
              type="button"
              class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
              @click="captureMode = null"
            >
              Revenir au choix
            </button>
          </div>
        </template>
      </section>
      <div class="space-y-4">
        <div
          v-if="info?.has_video"
          class="flex items-center justify-between gap-4 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
        >
          <div class="flex min-w-0 items-start gap-3">
            <UIcon name="i-lucide-sparkles" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
            <div class="min-w-0">
              <p class="text-sm font-semibold text-[var(--app-ink)]">Génération automatique</p>
              <p class="text-muted text-xs leading-relaxed">
                Chaque nouveau site démo génère sa vidéo tout seul, sans action de votre part.
              </p>
            </div>
          </div>
          <UiSwitch id="video-auto-generate" v-model="autoGenerate" />
        </div>
        <section
          v-if="info?.has_video"
          class="space-y-5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-4"
        >
          <div class="flex items-start gap-3">
            <UIcon name="i-lucide-scissors" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
            <div class="min-w-0">
              <p class="text-sm font-semibold text-[var(--app-ink)]">Déroulé de la vidéo</p>
              <p class="text-muted mt-0.5 text-xs leading-relaxed">
                Webcam plein écran, puis le site qui défile, puis l'éditeur Storyblok, puis votre appel à l'action.
                Réglez chaque partie pour coller à votre speech.
              </p>
            </div>
          </div>

          <div>
            <div
              class="flex h-9 w-full overflow-hidden rounded-lg border border-[var(--app-line)]"
              role="img"
              :aria-label="timelineAriaLabel"
            >
              <div
                v-for="segment in timelineSegments"
                :key="segment.key"
                :class="['flex min-w-0 items-center justify-center', segment.tone]"
                :style="{ width: segment.width }"
              >
                <span class="truncate px-1.5 text-[10px] font-semibold">{{ segment.shortLabel }}</span>
              </div>
            </div>
            <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[var(--app-ink-soft)]">
              <span
                v-for="segment in timelineSegments"
                :key="`legend-${segment.key}`"
                class="inline-flex items-center gap-1.5"
              >
                <span
                  :class="['h-2.5 w-2.5 shrink-0 rounded-sm border border-[var(--app-line)]', segment.tone]"
                  aria-hidden="true"
                />
                {{ segment.label }} · {{ formatSegment(segment.seconds) }}
              </span>
            </div>
          </div>

          <div :class="['grid gap-3', isRecordedClip ? 'max-w-xs grid-cols-1' : 'max-w-md grid-cols-3']">
            <div v-if="!isRecordedClip">
              <label class="text-muted mb-1.5 block text-xs font-medium" for="video-intro">Intro (s)</label>
              <input
                id="video-intro"
                v-model.number="introSeconds"
                type="number"
                min="0"
                max="30"
                step="0.5"
                class="input-field"
                placeholder="5"
              />
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="video-site">Partie site (s)</label>
              <input
                id="video-site"
                v-model.number="siteScrollSeconds"
                type="number"
                min="0"
                :max="Math.round(middleSeconds)"
                step="0.5"
                class="input-field"
                placeholder="12"
              />
            </div>
            <div v-if="!isRecordedClip">
              <label class="text-muted mb-1.5 block text-xs font-medium" for="video-outro">Outro (s)</label>
              <input
                id="video-outro"
                v-model.number="outroSeconds"
                type="number"
                min="0"
                max="30"
                step="0.5"
                class="input-field"
                placeholder="8"
              />
            </div>
          </div>
          <p v-if="isRecordedClip" class="text-muted text-xs leading-relaxed">
            Intro ({{ formatSegment(introSeconds) }}) et outro ({{ formatSegment(outroSeconds) }}) sont mesurées sur vos
            prises — seule la répartition site / Storyblok se règle.
          </p>
          <p class="text-muted text-xs leading-relaxed">
            Partie Storyblok :
            <span class="font-medium text-[var(--app-ink)]">{{ formatSegment(storyblokSegmentSeconds) }}</span>
            (le reste du milieu). Plus la partie site est longue, plus le défilement est lent.
          </p>
          <UiCallout v-if="isStoryblokSegmentShort" variant="warning">
            Moins de {{ STORYBLOK_COMFORT_SECONDS }} s pour la séquence Storyblok : la démonstration d'édition sera
            coupée avant la fin. Raccourcissez la partie site si vous voulez la montrer en entier.
          </UiCallout>

          <div v-if="isDesktopApp" class="space-y-3 border-t border-[var(--app-line)] pt-4">
            <div class="min-w-0">
              <p class="text-sm font-medium text-[var(--app-ink)]">Aperçu de calibration</p>
              <p class="text-muted mt-0.5 text-xs leading-relaxed">
                Générez un exemple complet avec l'un de vos sites, en local, avec les réglages ci-dessus — rien n'est
                publié, la vidéo réelle du site n'est pas touchée.
              </p>
            </div>
            <div class="flex flex-wrap items-end gap-3">
              <div class="min-w-56 flex-1">
                <label class="text-muted mb-1.5 block text-xs font-medium">Site d'exemple</label>
                <UiSelectField
                  v-model="previewSiteId"
                  :options="previewSiteOptions"
                  placeholder="Choisir un site démo"
                />
              </div>
              <button
                type="button"
                class="app-btn-secondary"
                :disabled="isBuildingPreview || !previewSiteId"
                @click="handleGeneratePreview"
              >
                <UIcon
                  :name="isBuildingPreview ? 'i-lucide-loader-circle' : 'i-lucide-play'"
                  :class="['h-3.5 w-3.5', isBuildingPreview && 'animate-spin']"
                />
                {{ isBuildingPreview ? 'Génération en cours (~2-3 min)…' : 'Générer un aperçu' }}
              </button>
            </div>
            <video
              v-if="previewVideoUrl"
              ref="previewPlayerRef"
              :key="previewVideoUrl"
              :src="previewVideoUrl"
              controls
              preload="auto"
              playsinline
              class="aspect-video w-full rounded-xl border border-[var(--app-line)] bg-black"
              @loadeddata="revealFirstFrame"
            />
          </div>
        </section>

        <UiCollapsibleCard
          v-if="captureMode !== 'record'"
          icon="i-lucide-clapperboard"
          title="Comment enregistrer votre clip"
        >
          <div class="space-y-6 px-4 py-5">
            <ol class="space-y-4">
              <li v-for="(step, index) in workflowSteps" :key="step.title" class="flex items-start gap-3">
                <span
                  class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] text-[11px] font-bold text-[var(--app-ink)]"
                >
                  {{ index + 1 }}
                </span>
                <div class="min-w-0 pt-0.5">
                  <p class="text-sm font-medium text-[var(--app-ink)]">{{ step.title }}</p>
                  <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ step.detail }}</p>
                </div>
              </li>
            </ol>
            <div class="space-y-4 rounded-lg bg-[var(--app-bg)] p-4">
              <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
                Le speech à lire (~45 s)
              </p>
              <div v-for="segment in speechSegments" :key="segment.timing" class="flex items-start gap-3">
                <span
                  class="mt-0.5 w-16 shrink-0 rounded-md bg-[var(--app-surface-2)] px-2 py-1 text-center text-[10px] font-bold tracking-wide text-[var(--app-ink-soft)] uppercase"
                >
                  {{ segment.timing }}
                </span>
                <div class="min-w-0">
                  <p class="text-[10px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
                    {{ segment.role }}
                  </p>
                  <p class="mt-0.5 text-sm leading-relaxed text-[var(--app-ink)] italic">« {{ segment.text }} »</p>
                </div>
              </div>
            </div>
            <div class="space-y-3">
              <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
                Conseils de tournage
              </p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="tip in RECORDING_TIPS"
                  :key="tip"
                  class="rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-1 text-xs text-[var(--app-ink)]"
                >
                  {{ tip }}
                </span>
              </div>
              <p class="text-muted flex items-start gap-2 text-xs leading-relaxed">
                <UIcon name="i-lucide-circle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
                <span>
                  <strong class="font-semibold text-[var(--app-ink)]">Restez générique</strong> : ne décrivez jamais une
                  section précise du site.
                </span>
              </p>
            </div>
          </div>
        </UiCollapsibleCard>
        <div v-if="info?.has_video" class="flex justify-end">
          <button type="button" class="btn-primary" :disabled="isSavingSettings" @click="handleSaveSettings">
            <UIcon v-if="isSavingSettings" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isSavingSettings ? 'Enregistrement…' : 'Enregistrer les réglages' }}
          </button>
        </div>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept="video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv"
        class="hidden"
        @change="handleFileSelected"
      />
    </template>

    <UiConfirmModal
      ref="deleteModalRef"
      title="Supprimer le clip"
      message="Supprimer votre clip de présentation ? Les vidéos déjà générées restent en ligne, mais plus aucune nouvelle vidéo ne pourra être créée tant qu'un clip n'est pas configuré."
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDeleteConfirmed"
    />

    <UiVideoGenerationModal
      :open="videoProgress.isOpen.value"
      title="Aperçu de calibration"
      :steps="videoProgress.steps.value"
      :log-lines="videoProgress.logLines.value"
      :elapsed-seconds="videoProgress.elapsedSeconds.value"
      :error-message="videoProgress.errorMessage.value"
      :is-running="videoProgress.isRunning.value"
      @close="videoProgress.close()"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseAuthReturn, UseToastReturn } from '~/types/Composables'
import type {
  PresenterVideoCaptureMode,
  PresenterVideoConfigEmits,
  PresenterVideoTimelineSegment,
} from '~/types/PresenterVideoConfig'
import type { ComputedRef, EmitFn, Ref } from 'vue'
import type { PresenterVideo } from '~/services/presenterVideoService'
import type { DemoSite, DemoSiteListResponse } from '~/services/demoSiteService'
import type { PreviewVideoResult } from '~/services/storyblokSidecarService'
import type { SelectFieldOption } from '~/types/SelectField'
import type { ProspectionScriptSegment } from '~/composables/useProspectionScript'
import type { UseVideoCompressionReturn, VideoCompressionResult } from '~/composables/useVideoCompression'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { PresenterVideoService } from '~/services/presenterVideoService'
import { DemoSiteService } from '~/services/demoSiteService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import type { UseVideoGenerationProgressReturn } from '~/composables/useVideoGenerationProgress'
import { useVideoGenerationProgress } from '~/composables/useVideoGenerationProgress'
import { buildDefaultScript } from '~/composables/useProspectionScript'
import { PRESENTER_VIDEO_MAX_BYTES, useVideoCompression } from '~/composables/useVideoCompression'
import { useToast } from '~/composables/useToast'
import { useAuth } from '~/composables/useAuth'

/** Presenter video upload, tuning and deletion for prospect videos. */

const emit: EmitFn<PresenterVideoConfigEmits> = defineEmits<PresenterVideoConfigEmits>()

/** The two ways in, offered side by side when no clip exists yet. */
const CAPTURE_OPTIONS: Array<{
  mode: PresenterVideoCaptureMode
  icon: string
  title: string
  detail: string
  badge: string
}> = [
  {
    mode: 'record',
    icon: 'i-lucide-video',
    title: 'Filmer ici, avec le texte à lire',
    detail:
      'Trois prises courtes — intro, milieu, fin — guidées par un prompteur. Chacune se refait toute seule si elle ne vous plaît pas.',
    badge: 'Le plus simple',
  },
  {
    mode: 'import',
    icon: 'i-lucide-upload',
    title: 'Importer un fichier',
    detail: 'Vous avez déjà filmé, au reflex, au téléphone ou avec un autre outil ? Déposez le fichier ici.',
    badge: '',
  },
]

/** Short recording tips rendered as pills. */
const RECORDING_TIPS: string[] = ['1080p suffit', 'Lumière face à vous', 'Regardez l’objectif']

/** Mirror of the server's automatic split: Storyblok budget carved out of the middle. */
const AUTO_STORYBLOK_SECONDS: number = 17

/** Mirror of the server's floor for the site-scroll part. */
const MIN_SITE_SCROLL_SECONDS: number = 6

/** Under this, the scripted Storyblok edit demo gets visibly cut. */
const STORYBLOK_COMFORT_SECONDS: number = 10

const toast: UseToastReturn = useToast()
const { user }: UseAuthReturn = useAuth()
const videoProgress: UseVideoGenerationProgressReturn = useVideoGenerationProgress()
const { isCompressing, compressionProgress, compressPresenterClip }: UseVideoCompressionReturn = useVideoCompression()

const info: Ref<PresenterVideo | null> = ref(null)
const previewUrl: Ref<string | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const isUploading: Ref<boolean> = ref(false)
const isSavingSettings: Ref<boolean> = ref(false)
const isDeleting: Ref<boolean> = ref(false)
const isDragging: Ref<boolean> = ref(false)
const selectedFile: Ref<File | null> = ref(null)
const fileInputRef: Ref<HTMLInputElement | null> = ref(null)
const deleteModalRef: Ref<{ open: () => void } | null> = ref(null)
const introSeconds: Ref<number> = ref(4)
const outroSeconds: Ref<number> = ref(5)
const siteScrollSeconds: Ref<number> = ref(12)
const autoGenerate: Ref<boolean> = ref(true)
const captureMode: Ref<PresenterVideoCaptureMode | null> = ref(null)

/** Whether the app runs in the desktop shell (the calibration preview needs the sidecar). */
const isDesktopApp: Ref<boolean> = ref(false)

/** Demo site used as the calibration example, as a select value. */
const previewSiteId: Ref<string> = ref('')
const previewSites: Ref<DemoSite[]> = ref([])
const isBuildingPreview: Ref<boolean> = ref(false)

/** The calibration preview <video>, scrolled into view once the render lands. */
const previewPlayerRef: Ref<HTMLVideoElement | null> = ref(null)

/** Object URL of the locally rendered calibration example. */
const previewVideoUrl: Ref<string | null> = ref(null)

/** Playable preview of the clip just picked, before it is sent. */
const pickedClipPreviewUrl: Ref<string | null> = ref(null)

/** Weight of the picked clip before compression, to show what was gained. */
const pickedClipOriginalBytes: Ref<number | null> = ref(null)

/** Blocking message when the picked clip is still too heavy to be sent. */
const clipSizeErrorMessage: Ref<string | null> = ref(null)

/** Whether the capture UI is shown on purpose while a clip already exists. */
const isReplacingClip: Ref<boolean> = ref(false)

/** Whether the stored clip is registered but its file cannot be fetched. */
const isClipFileMissing: Ref<boolean> = ref(false)

/** Whether the stored clip was filmed in-app (its cut points are measured). */
const isRecordedClip: ComputedRef<boolean> = computed((): boolean => info.value?.source === 'recorded')

/** Speech segments aligned with the in-app teleprompter script. */
const speechSegments: ComputedRef<Array<{ timing: string; role: string; text: string }>> = computed(
  (): Array<{ timing: string; role: string; text: string }> =>
    buildDefaultScript(user.value?.name ?? '', user.value?.company_name ?? '').map(
      (segment: ProspectionScriptSegment): { timing: string; role: string; text: string } => ({
        timing: `~${segment.targetSeconds} s`,
        role: segment.title,
        text: segment.text,
      }),
    ),
)

/** The three steps of the folded guide, worded for the chosen capture method. */
const workflowSteps: ComputedRef<Array<{ title: string; detail: string }>> = computed(
  (): Array<{ title: string; detail: string }> => [
    {
      title: 'Filmez-vous ~45 s, une seule fois',
      detail:
        captureMode.value === 'import'
          ? 'Webcam + micro, face caméra, en lisant le speech ci-dessous.'
          : 'En trois prises courtes dans l’application, ou avec l’outil de votre choix puis en important le fichier.',
    },
    {
      title: captureMode.value === 'import' ? 'Déposez le fichier' : 'Gardez vos prises',
      detail: 'C’est votre seule action : le découpage et la personnalisation sont ensuite automatiques.',
    },
    {
      title: 'Chaque prospect reçoit sa vidéo',
      detail:
        'Son site défile à l’écran, son prénom en incrustation. La vignette cliquable s’ajoute à vos emails via {vignette_video} — ou via l’un des deux modèles « Vidéo » déjà prêts.',
    },
  ],
)

/** Whether the stored clip is shown in its player rather than the capture UI. */
const showClipPlayer: ComputedRef<boolean> = computed(
  (): boolean => Boolean(info.value?.has_video) && previewUrl.value !== null && !isReplacingClip.value,
)

/** Clip length, spelled out next to the player. */
const clipDurationLabel: ComputedRef<string> = computed((): string => {
  const seconds: number | undefined = info.value?.duration_seconds
  if (!seconds) return ''
  return `${Math.round(seconds)} s`
})

/** Show the capture choice again, keeping the current clip until a new one is saved. */
function startClipReplacement(): void {
  captureMode.value = null
  isReplacingClip.value = true
}

/** Seconds between intro and outro — shared by the site scroll and the Storyblok sequence. */
const middleSeconds: ComputedRef<number> = computed((): number => {
  const duration: number = info.value?.duration_seconds ?? 0
  return Math.max(0, duration - introSeconds.value - outroSeconds.value)
})

/** Seconds left for the Storyblok editor sequence (the middle minus the site part). */
const storyblokSegmentSeconds: ComputedRef<number> = computed((): number =>
  Math.max(0, middleSeconds.value - siteScrollSeconds.value),
)

/** Whether the Storyblok demo will be visibly cut with the current split. */
const isStoryblokSegmentShort: ComputedRef<boolean> = computed(
  (): boolean => Boolean(info.value?.has_video) && storyblokSegmentSeconds.value < STORYBLOK_COMFORT_SECONDS,
)

/** The four parts of the timeline bar, widths proportional to their durations. */
const timelineSegments: ComputedRef<PresenterVideoTimelineSegment[]> = computed((): PresenterVideoTimelineSegment[] => {
  const duration: number = info.value?.duration_seconds ?? 0
  if (duration <= 0) return []
  const parts: Array<Omit<PresenterVideoTimelineSegment, 'width'>> = [
    {
      key: 'intro',
      label: 'Intro webcam',
      shortLabel: 'Intro',
      seconds: introSeconds.value,
      tone: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
    },
    {
      key: 'site',
      label: 'Site qui défile',
      shortLabel: 'Site',
      seconds: Math.min(siteScrollSeconds.value, middleSeconds.value),
      tone: 'bg-[var(--app-ink)] text-[var(--app-bg)]',
    },
    {
      key: 'storyblok',
      label: 'Éditeur Storyblok',
      shortLabel: 'Storyblok',
      seconds: storyblokSegmentSeconds.value,
      tone: 'bg-[var(--app-ink-soft)] text-[var(--app-bg)]',
    },
    {
      key: 'outro',
      label: 'Outro webcam',
      shortLabel: 'Outro',
      seconds: outroSeconds.value,
      tone: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
    },
  ]
  return parts.map(
    (part: Omit<PresenterVideoTimelineSegment, 'width'>): PresenterVideoTimelineSegment => ({
      ...part,
      width: `${Math.max(2, (part.seconds / duration) * 100)}%`,
    }),
  )
})

/** Select options for the calibration example, from the loaded demo sites. */
const previewSiteOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] =>
  previewSites.value.map(
    (site: DemoSite): SelectFieldOption => ({ value: String(site.id), label: site.business_name }),
  ),
)

/** Spoken description of the timeline for assistive tech. */
const timelineAriaLabel: ComputedRef<string> = computed((): string =>
  timelineSegments.value
    .map((segment: PresenterVideoTimelineSegment): string => `${segment.label} ${formatSegment(segment.seconds)}`)
    .join(', '),
)

/**
 * Release the current preview object URL (avoids leaking blobs).
 */
function releasePreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
}

/**
 * Sync the local form state from a fresh API payload.
 * @param payload - Clip metadata returned by the API.
 */
function applyInfo(payload: PresenterVideo): void {
  info.value = payload
  introSeconds.value = payload.intro_seconds ?? 4
  outroSeconds.value = payload.outro_seconds ?? 5
  siteScrollSeconds.value = payload.site_seconds ?? autoSiteSeconds(payload)
  autoGenerate.value = payload.auto_generate ?? true
}

/**
 * Effective site-scroll seconds before a custom split is saved (server's automatic split).
 * @param payload - Clip metadata.
 * @returns The middle minus the Storyblok budget, floored like the server does.
 */
function autoSiteSeconds(payload: PresenterVideo): number {
  const middle: number = Math.max(
    0,
    (payload.duration_seconds ?? 0) - (payload.intro_seconds ?? 4) - (payload.outro_seconds ?? 5),
  )
  return Math.max(MIN_SITE_SCROLL_SECONDS, Math.round((middle - AUTO_STORYBLOK_SECONDS) * 2) / 2)
}

/**
 * Load the clip metadata + preview blob from the API.
 */
async function loadInfo(): Promise<void> {
  isLoading.value = true
  isClipFileMissing.value = false
  try {
    applyInfo(await PresenterVideoService.getPresenterVideo())
    isReplacingClip.value = false
    releasePreview()
    if (!info.value?.has_video) return
    previewUrl.value = await PresenterVideoService.getPresenterVideoObjectUrl()
    // Le service renvoie null sur une 404 : enregistrement présent, fichier absent du stockage.
    isClipFileMissing.value = previewUrl.value === null
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger le clip')
  } finally {
    isLoading.value = false
  }
}

/** Force the first decoded frame so the preview is not a black box on load. */
function revealFirstFrame(event: Event): void {
  const video: HTMLVideoElement | null = event.target as HTMLVideoElement | null
  if (!video || video.currentTime > 0) return
  try {
    video.currentTime = Math.min(0.1, (video.duration || 1) / 2)
  } catch {
    // Some engines throw if the media is not seekable yet — safe to ignore.
  }
}

/**
 * Format a cut point for the read-only « découpage automatique » line.
 * @param seconds - Segment length.
 * @returns A short label (e.g. « 4,5 s »).
 */
function formatSegment(seconds: number): string {
  return `${seconds.toFixed(1).replace(/\.0$/, '').replace('.', ',')} s`
}

/**
 * Adopt the clip just assembled from the three in-app takes.
 * @param payload - Fresh clip metadata returned by the API.
 */
async function handleRecorded(payload: PresenterVideo): Promise<void> {
  applyInfo(payload)
  captureMode.value = null
  isReplacingClip.value = false
  releasePreview()
  previewUrl.value = await PresenterVideoService.getPresenterVideoObjectUrl()
}

/**
 * Open the hidden file input from the drop zone.
 */
function openFilePicker(): void {
  fileInputRef.value?.click()
}

/**
 * Keep the selected file from the input change event.
 * @param event - Native change event of the file input.
 */
async function handleFileSelected(event: Event): Promise<void> {
  const input: HTMLInputElement | null = event.target as HTMLInputElement | null
  const file: File | null = input?.files?.[0] ?? null
  if (file) await adoptPickedClip(file)
}

/**
 * Accept a file dropped on the drop zone.
 * @param file - The dropped file.
 */
async function handleDropFile(file: File): Promise<void> {
  await adoptPickedClip(file)
}

/** Drop the preview of the clip awaiting upload (avoids leaking blobs). */
function releasePickedClipPreview(): void {
  if (pickedClipPreviewUrl.value) {
    URL.revokeObjectURL(pickedClipPreviewUrl.value)
    pickedClipPreviewUrl.value = null
  }
}

/** Forget the clip awaiting upload, along with its preview and messages. */
function resetPickedClip(): void {
  releasePickedClipPreview()
  selectedFile.value = null
  pickedClipOriginalBytes.value = null
  clipSizeErrorMessage.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

/**
 * Show a picked clip right away, then shrink it to the montage canvas.
 *
 * Compression is transparent: the user drops a file and sees the preview, the
 * final weight, and — if the clip still cannot be sent — why.
 *
 * @param file - The clip dropped on the zone or chosen in the file picker.
 */
async function adoptPickedClip(file: File): Promise<void> {
  // Two concurrent re-encodings would race to overwrite `selectedFile`.
  if (isCompressing.value || isUploading.value) return

  releasePickedClipPreview()
  selectedFile.value = file
  pickedClipOriginalBytes.value = null
  clipSizeErrorMessage.value = null
  pickedClipPreviewUrl.value = URL.createObjectURL(file)

  const result: VideoCompressionResult = await compressPresenterClip(file)
  selectedFile.value = result.file
  pickedClipOriginalBytes.value = result.wasCompressed ? result.originalBytes : null
  clipSizeErrorMessage.value = describeOversizedClip(result)
}

/**
 * Explain, in the user's terms, why a clip cannot be sent as-is.
 *
 * Returning `null` means the clip is good to go.
 *
 * @param result - Outcome of the compression attempt.
 * @returns A sentence naming the fix, or `null` when the clip fits.
 */
function describeOversizedClip(result: VideoCompressionResult): string | null {
  if (result.file.size <= PRESENTER_VIDEO_MAX_BYTES) return null

  const currentMb: number = Math.round(result.file.size / (1024 * 1024))
  const maxMb: number = Math.round(PRESENTER_VIDEO_MAX_BYTES / (1024 * 1024))
  const limits: string = `Cette vidéo pèse ${currentMb} Mo, au-delà de la limite d'envoi de ${maxMb} Mo.`

  if (result.skipReason === 'undecodable') {
    return `${limits} Son format n'a pas pu être lu ici pour l'alléger automatiquement — ré-exportez-la en MP4 (H.264), 720p suffit.`
  }
  return `${limits} Ré-exportez-la en 720p ou raccourcissez-la (30 à 45 s suffisent).`
}

/**
 * Upload the selected clip (replaces the previous one server-side).
 */
async function handleUpload(): Promise<void> {
  if (!selectedFile.value || isCompressing.value) return

  // Without this guard the request dies in nginx, surfacing as « Failed to fetch ».
  if (selectedFile.value.size > PRESENTER_VIDEO_MAX_BYTES) {
    toast.error(clipSizeErrorMessage.value ?? 'Cette vidéo est trop lourde pour être envoyée.')
    return
  }

  isUploading.value = true
  try {
    applyInfo(
      await PresenterVideoService.uploadPresenterVideo(
        selectedFile.value,
        introSeconds.value,
        outroSeconds.value,
        autoGenerate.value,
      ),
    )
    resetPickedClip()
    isReplacingClip.value = false
    releasePreview()
    previewUrl.value = await PresenterVideoService.getPresenterVideoObjectUrl()
    toast.success('Clip de présentation enregistré — les prochains sites généreront leur vidéo automatiquement')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi du clip")
  } finally {
    isUploading.value = false
  }
}

/**
 * Persist the segment cuts + auto-generation toggle.
 */
async function handleSaveSettings(): Promise<void> {
  isSavingSettings.value = true
  try {
    applyInfo(
      await PresenterVideoService.updatePresenterVideoSettings(
        introSeconds.value,
        outroSeconds.value,
        autoGenerate.value,
        siteScrollSeconds.value,
      ),
    )
    toast.success('Réglages enregistrés')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la mise à jour')
  } finally {
    isSavingSettings.value = false
  }
}

/** Load the demo sites usable as calibration examples (those with a public URL). */
async function loadPreviewSites(): Promise<void> {
  try {
    const response: DemoSiteListResponse = await DemoSiteService.listDemoSites()
    previewSites.value = response.items.filter((site: DemoSite): boolean => Boolean(site.demo_url))
    if (!previewSiteId.value && previewSites.value.length > 0) {
      previewSiteId.value = String(previewSites.value[0]!.id)
    }
  } catch {
    // Pas bloquant : le sélecteur reste vide et le bouton d'aperçu désactivé.
  }
}

/** Release the calibration preview's object URL (avoids leaking blobs). */
function releaseCalibrationPreview(): void {
  if (previewVideoUrl.value) {
    URL.revokeObjectURL(previewVideoUrl.value)
    previewVideoUrl.value = null
  }
}

/**
 * Render a calibration example locally with the CURRENT (possibly unsaved) timings.
 *
 * Nothing is published: the sidecar returns the mp4 straight back and it plays inline,
 * so the split can be adjusted like in a video editor before saving.
 */
async function handleGeneratePreview(): Promise<void> {
  if (!previewSiteId.value) return
  const chosenSite: DemoSite | undefined = previewSites.value.find(
    (candidate: DemoSite): boolean => String(candidate.id) === previewSiteId.value,
  )
  isBuildingPreview.value = true
  videoProgress.start(chosenSite?.slug ?? '', "Récupération de l'aperçu")
  try {
    const result: PreviewVideoResult = await StoryblokSidecarService.buildPreviewVideo(Number(previewSiteId.value), {
      presenter_intro: introSeconds.value,
      presenter_outro: outroSeconds.value,
      site_seconds: siteScrollSeconds.value,
      total_seconds: middleSeconds.value,
    })
    if (result.status === 'done' && result.video) {
      videoProgress.finish()
      releaseCalibrationPreview()
      previewVideoUrl.value = URL.createObjectURL(result.video)
      videoProgress.close()
      toast.success('Aperçu prêt — rien n’a été publié')
      await nextTick()
      previewPlayerRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      return
    }
    if (result.status === 'needs_login') {
      videoProgress.close()
      toast.error('Session Storyblok expirée — reconnectez-vous via la carte « Connexion Storyblok ».')
      return
    }
    if (result.status === 'unavailable') {
      videoProgress.close()
      toast.error("Disponible uniquement dans l'application desktop.")
      return
    }
    videoProgress.fail(result.message ?? "Échec de la génération de l'aperçu.")
    toast.error(result.message ?? "Échec de la génération de l'aperçu.")
  } catch (error) {
    const message: string = error instanceof Error ? error.message : "Échec de la génération de l'aperçu."
    videoProgress.fail(message)
    toast.error(message)
  } finally {
    isBuildingPreview.value = false
  }
}

/**
 * Open the delete confirmation modal.
 */
function askDeleteClip(): void {
  deleteModalRef.value?.open()
}

/**
 * Delete the clip once confirmed in the modal.
 */
async function handleDeleteConfirmed(): Promise<void> {
  isDeleting.value = true
  try {
    applyInfo(await PresenterVideoService.deletePresenterVideo())
    isReplacingClip.value = false
    releasePreview()
    // Repartir du choix, pas de la méthode utilisée la fois précédente.
    captureMode.value = null
    toast.success('Clip supprimé')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    isDeleting.value = false
  }
}

// Let the host know whether a clip is in place (used by the setup wizard).
watch(
  (): boolean => Boolean(info.value?.has_video),
  (hasVideo: boolean): void => {
    emit('has-video', hasVideo)
  },
)

// Shrinking the middle (longer intro/outro) must never leave the site part overflowing it.
watch(middleSeconds, (middle: number): void => {
  if (siteScrollSeconds.value > middle) {
    siteScrollSeconds.value = Math.max(0, Math.round(middle * 2) / 2)
  }
})

onMounted(async (): Promise<void> => {
  await loadInfo()
  isDesktopApp.value = (await getScraperSidecarInfo()) !== null
  if (isDesktopApp.value) await loadPreviewSites()
})

onBeforeUnmount((): void => {
  releasePreview()
  releasePickedClipPreview()
  releaseCalibrationPreview()
})
</script>
