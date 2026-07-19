<template>
  <div class="mx-auto max-w-2xl space-y-8">
    <!-- Header — one calm line -->
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Vidéo de prospection</h1>
      <p class="text-muted mt-2 text-sm leading-relaxed">
        Un clip webcam enregistré une seule fois. Chaque site démo génère ensuite sa vidéo personnalisée, prête pour vos
        emails.
      </p>
    </div>

    <UiLoader v-if="isLoading" />

    <template v-else>
      <!-- ── Le clip ───────────────────────────────────────────────────────── -->
      <section class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Votre clip</h2>
          <span v-if="info?.has_video" class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Prêt
          </span>
        </div>

        <!-- Present: preview + a round red delete button top-right -->
        <div v-if="info?.has_video && previewUrl" class="relative">
          <video
            :src="previewUrl"
            controls
            playsinline
            preload="metadata"
            class="aspect-video w-full rounded-xl border border-[var(--app-line)] bg-black"
          />
          <button
            type="button"
            class="btn-danger absolute top-3 right-3 z-10 h-9 w-9 !p-0 disabled:opacity-50"
            :disabled="isDeleting"
            aria-label="Supprimer le clip"
            title="Supprimer le clip"
            @click="askDeleteClip"
          >
            <UIcon
              :name="isDeleting ? 'i-lucide-loader-circle' : 'i-lucide-trash-2'"
              :class="['h-4 w-4', isDeleting && 'animate-spin']"
            />
          </button>
        </div>

        <!-- Absent: the drop zone takes the clip's place -->
        <UiPresenterVideoDropzone
          v-else
          :selected-file="selectedFile"
          :is-dragging="isDragging"
          :is-uploading="isUploading"
          @pick="openFilePicker"
          @drop-file="handleDropFile"
          @dragging="isDragging = $event"
          @upload="handleUpload"
        />
      </section>

      <!-- ── Les trois cartes de réglages, puis « Enregistrer » tout en bas ── -->
      <div class="space-y-4">
        <!-- Génération automatique (avec un clip en place) -->
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

        <!-- Découpage (replié, avec un clip en place) -->
        <UiCollapsibleCard
          v-if="info?.has_video"
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

        <!-- ── Comment enregistrer votre clip (toujours visible) ────────────── -->
        <UiCollapsibleCard icon="i-lucide-clapperboard" title="Comment enregistrer votre clip">
          <div class="space-y-6 px-4 py-5">
            <!-- Les 3 étapes -->
            <ol class="space-y-4">
              <li v-for="(step, index) in WORKFLOW_STEPS" :key="step.title" class="flex items-start gap-3">
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

            <!-- Le speech, mis en valeur dans un encart -->
            <div class="space-y-4 rounded-lg bg-[var(--app-bg)] p-4">
              <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
                Le speech à lire (~30 s, voix générique)
              </p>
              <div v-for="segment in SPEECH_SEGMENTS" :key="segment.timing" class="flex items-start gap-3">
                <span
                  class="mt-0.5 w-16 shrink-0 rounded-md bg-[var(--app-surface-2)] px-2 py-1 text-center text-[10px] font-bold tracking-wide text-[var(--app-ink-soft)] uppercase"
                >
                  {{ segment.timing }}
                </span>
                <p class="min-w-0 text-sm leading-relaxed text-[var(--app-ink)] italic">« {{ segment.text }} »</p>
              </div>
            </div>

            <!-- Conseils de tournage -->
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

        <!-- Enregistrer, tout en bas des trois cartes -->
        <div v-if="info?.has_video" class="flex justify-end">
          <button type="button" class="btn-primary" :disabled="isSavingSettings" @click="handleSaveSettings">
            <UIcon v-if="isSavingSettings" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isSavingSettings ? 'Enregistrement…' : 'Enregistrer les réglages' }}
          </button>
        </div>
      </div>

      <!-- Le fichier réel, partagé par la dropzone -->
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
import type { ComputedRef, Ref } from 'vue'
import type { PresenterVideoInfo } from '~/services/presenterVideoService'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  deletePresenterVideo,
  getPresenterVideo,
  getPresenterVideoObjectUrl,
  updatePresenterVideoSettings,
  uploadPresenterVideo,
} from '~/services/presenterVideoService'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

/** The three steps shown in the folded « Comment enregistrer votre clip » guide. */
const WORKFLOW_STEPS: Array<{ title: string; detail: string }> = [
  {
    title: 'Filmez-vous ~30 s, une seule fois',
    detail: 'Webcam + micro, face caméra, en lisant le speech ci-dessous.',
  },
  {
    title: 'Déposez le fichier',
    detail: 'C’est votre seule action : le découpage et la personnalisation sont ensuite automatiques.',
  },
  {
    title: 'Chaque prospect reçoit sa vidéo',
    detail:
      'Son site défile à l’écran, son prénom en incrustation. La vignette cliquable s’ajoute à vos emails via {vignette_video} — ou via l’un des deux modèles « Vidéo » déjà prêts.',
  },
]

/** Recommended generic speech, segment by segment (~30 s total). */
const SPEECH_SEGMENTS: Array<{ timing: string; text: string }> = [
  { timing: '0 - 4 s', text: "Bonjour ! Moi c'est Léo, développeur web." },
  {
    timing: '4 - 27 s',
    text:
      "Si je vous contacte, c'est que j'ai déjà créé un site web pour votre entreprise — vous êtes en train de le voir. " +
      'Il est en ligne, à votre nom, avec vos informations. Et surtout : vous pouvez tout modifier vous-même — ' +
      'textes, photos, horaires — sans développeur, depuis un espace d’administration très simple.',
  },
  { timing: '27 - 32 s', text: 'Cliquez sur le lien juste en dessous pour le découvrir en vrai. À tout de suite !' },
]

/** Short recording tips rendered as pills. */
const RECORDING_TIPS: string[] = ['1080p suffit', 'Lumière face à vous', 'Regardez l’objectif']

const toast = useToast()

const info: Ref<PresenterVideoInfo | null> = ref<PresenterVideoInfo | null>(null)
const previewUrl: Ref<string | null> = ref<string | null>(null)
const isLoading: Ref<boolean> = ref<boolean>(true)
const isUploading: Ref<boolean> = ref<boolean>(false)
const isSavingSettings: Ref<boolean> = ref<boolean>(false)
const isDeleting: Ref<boolean> = ref<boolean>(false)
const isDragging: Ref<boolean> = ref<boolean>(false)
const selectedFile: Ref<File | null> = ref<File | null>(null)
const fileInputRef: Ref<HTMLInputElement | null> = ref<HTMLInputElement | null>(null)
const deleteModalRef: Ref<{ open: () => void } | null> = ref<{ open: () => void } | null>(null)
const introSeconds: Ref<number> = ref<number>(4)
const outroSeconds: Ref<number> = ref<number>(5)
const autoGenerate: Ref<boolean> = ref<boolean>(true)

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
function applyInfo(payload: PresenterVideoInfo): void {
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
    applyInfo(await getPresenterVideo())
    releasePreview()
    if (info.value?.has_video) {
      previewUrl.value = await getPresenterVideoObjectUrl()
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger le clip')
  } finally {
    isLoading.value = false
  }
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
  const input = event.target as HTMLInputElement | null
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
      await uploadPresenterVideo(selectedFile.value, introSeconds.value, outroSeconds.value, autoGenerate.value),
    )
    selectedFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    releasePreview()
    previewUrl.value = await getPresenterVideoObjectUrl()
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
    applyInfo(await updatePresenterVideoSettings(introSeconds.value, outroSeconds.value, autoGenerate.value))
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
    applyInfo(await deletePresenterVideo())
    releasePreview()
    toast.success('Clip supprimé')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    isDeleting.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadInfo()
})

onBeforeUnmount((): void => {
  releasePreview()
})
</script>
