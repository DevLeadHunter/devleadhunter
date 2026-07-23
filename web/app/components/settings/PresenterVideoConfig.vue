<template>
  <div class="space-y-8">
    <UiLoader v-if="isLoading" />

    <template v-else>
      <section class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Votre clip</h2>
          <span v-if="info?.has_video" class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Prêt
          </span>
        </div>
        <div v-if="info?.has_video && previewUrl" class="relative">
          <video
            :src="previewUrl"
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
        <template v-else>
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
        <div
          v-if="info?.has_video && isRecordedClip"
          class="flex items-start gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
        >
          <UIcon name="i-lucide-scissors" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
          <div class="min-w-0">
            <p class="text-sm font-semibold text-[var(--app-ink)]">Découpage automatique</p>
            <p class="text-muted mt-0.5 text-xs leading-relaxed">
              Clip filmé dans l'application : chaque prise est un segment, donc les coupes sont exactes — intro
              {{ formatSegment(introSeconds) }}, site
              <template v-if="siteSegmentSeconds !== null">{{ siteSegmentSeconds }} s</template>
              <template v-else>—</template>
              , outro {{ formatSegment(outroSeconds) }}. Rien à régler.
            </p>
          </div>
        </div>
        <UiCollapsibleCard
          v-if="info?.has_video && !isRecordedClip"
          icon="i-lucide-scissors"
          title="Découpage de la vidéo"
          suffix="facultatif"
        >
          <div class="space-y-4 px-4 py-4">
            <p class="text-muted text-xs leading-relaxed">
              Webcam plein écran au début (« Bonjour {Prénom} ») et à la fin (votre appel à l'action) ; entre les deux,
              le site du prospect défile avec votre webcam en pastille.
            </p>
            <div class="grid max-w-xs grid-cols-2 gap-3">
              <div>
                <label class="text-muted mb-1.5 block text-xs font-medium" for="video-intro">Intro (s)</label>
                <input
                  id="video-intro"
                  v-model.number="introSeconds"
                  type="number"
                  min="0"
                  max="30"
                  step="0.5"
                  class="input-field"
                />
              </div>
              <div>
                <label class="text-muted mb-1.5 block text-xs font-medium" for="video-outro">Outro (s)</label>
                <input
                  id="video-outro"
                  v-model.number="outroSeconds"
                  type="number"
                  min="0"
                  max="30"
                  step="0.5"
                  class="input-field"
                />
              </div>
            </div>
            <p v-if="siteSegmentSeconds !== null" class="text-muted text-xs">
              Site du prospect à l'écran :
              <span class="font-medium text-[var(--app-ink)]">{{ siteSegmentSeconds }} s</span>
            </p>
          </div>
        </UiCollapsibleCard>

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
                Le speech à lire (~30 s)
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
  </div>
</template>

<script lang="ts" setup>
import type { UseAuthReturn, UseToastReturn } from '~/types/Composables'
import type { PresenterVideoCaptureMode, PresenterVideoConfigEmits } from '~/types/PresenterVideoConfig'
import type { ComputedRef, EmitFn, Ref } from 'vue'
import type { PresenterVideo } from '~/services/presenterVideoService'
import type { ProspectionScriptSegment } from '~/composables/useProspectionScript'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { PresenterVideoService } from '~/services/presenterVideoService'
import { buildDefaultScript } from '~/composables/useProspectionScript'
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

const toast: UseToastReturn = useToast()
const { user }: UseAuthReturn = useAuth()

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
const autoGenerate: Ref<boolean> = ref(true)
const captureMode: Ref<PresenterVideoCaptureMode | null> = ref(null)

/** Whether the stored clip was filmed in-app (its cut points are measured). */
const isRecordedClip: ComputedRef<boolean> = computed((): boolean => info.value?.source === 'recorded')

/** Speech segments aligned with the in-app teleprompter script. */
const speechSegments: ComputedRef<Array<{ timing: string; role: string; text: string }>> = computed(
  (): Array<{ timing: string; role: string; text: string }> =>
    buildDefaultScript(user.value?.name ?? '').map(
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
      title: 'Filmez-vous ~30 s, une seule fois',
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

/** Seconds left for the site-scroll segment (duration - intro - outro). */
const siteSegmentSeconds: ComputedRef<number | null> = computed((): number | null => {
  if (!info.value?.has_video || !info.value.duration_seconds) return null
  return Math.max(0, Math.round(info.value.duration_seconds - introSeconds.value - outroSeconds.value))
})

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
  autoGenerate.value = payload.auto_generate ?? true
}

/**
 * Load the clip metadata + preview blob from the API.
 */
async function loadInfo(): Promise<void> {
  isLoading.value = true
  try {
    applyInfo(await PresenterVideoService.getPresenterVideo())
    releasePreview()
    if (info.value?.has_video) {
      previewUrl.value = await PresenterVideoService.getPresenterVideoObjectUrl()
    }
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
function handleFileSelected(event: Event): void {
  const input: HTMLInputElement | null = event.target as HTMLInputElement | null
  selectedFile.value = input?.files?.[0] ?? null
}

/**
 * Accept a file dropped on the drop zone.
 * @param file - The dropped file.
 */
function handleDropFile(file: File): void {
  selectedFile.value = file
}

/**
 * Upload the selected clip (replaces the previous one server-side).
 */
async function handleUpload(): Promise<void> {
  if (!selectedFile.value) return
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
    selectedFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
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
 * Persist the intro/outro segments + auto-generation toggle.
 */
async function handleSaveSettings(): Promise<void> {
  isSavingSettings.value = true
  try {
    applyInfo(
      await PresenterVideoService.updatePresenterVideoSettings(
        introSeconds.value,
        outroSeconds.value,
        autoGenerate.value,
      ),
    )
    toast.success('Réglages enregistrés')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la mise à jour')
  } finally {
    isSavingSettings.value = false
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

onMounted(async (): Promise<void> => {
  await loadInfo()
})

onBeforeUnmount((): void => {
  releasePreview()
})
</script>
