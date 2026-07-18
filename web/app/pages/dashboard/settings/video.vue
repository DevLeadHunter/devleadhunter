<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Vidéo de prospection</h1>
      <p class="text-muted mt-2 text-sm">
        Configurez une fois votre clip webcam générique — chaque site démo généré produira ensuite automatiquement sa
        vidéo personnalisée, prête à insérer dans vos emails.
      </p>
    </div>

    <!-- Principe (court) -->
    <UiCallout variant="info">
      Une seule vidéo webcam (30-45&nbsp;s, voix
      <strong class="font-medium text-[var(--app-ink)]">100 % générique</strong>) est réutilisée pour tous les prospects
      — la personnalisation passe par l'image : son site à l'écran, son prénom en texte.
    </UiCallout>

    <!-- Comment ça marche -->
    <div class="card">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Comment ça marche</h2>
      <ol class="space-y-3">
        <li v-for="(step, index) in WORKFLOW_STEPS" :key="step.title" class="flex items-start gap-3">
          <span
            class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--app-ink)] text-[11px] font-bold text-[var(--app-surface)]"
          >
            {{ index + 1 }}
          </span>
          <div class="min-w-0">
            <p class="text-sm font-medium text-[var(--app-ink)]">{{ step.title }}</p>
            <p class="text-muted text-xs leading-relaxed">{{ step.detail }}</p>
          </div>
        </li>
      </ol>
    </div>

    <!-- Speech recommandé (dépliable) -->
    <div class="card p-0">
      <button
        type="button"
        class="flex w-full cursor-pointer items-center justify-between gap-3 px-6 py-4 text-left transition-colors hover:bg-[var(--app-surface-2)]"
        @click="isSpeechOpen = !isSpeechOpen"
      >
        <span class="flex items-center gap-2 text-sm font-semibold text-[var(--app-ink)]">
          <UIcon name="i-lucide-scroll-text" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          Le speech recommandé (~30 s) — à lire avant d'enregistrer
        </span>
        <UIcon
          :name="isSpeechOpen ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
          class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]"
        />
      </button>
      <div v-if="isSpeechOpen" class="space-y-4 border-t border-[var(--app-line)] px-6 py-5">
        <div v-for="segment in SPEECH_SEGMENTS" :key="segment.timing" class="flex items-start gap-3">
          <span
            class="mt-0.5 w-24 shrink-0 rounded-md bg-[var(--app-surface-2)] px-2 py-1 text-center text-[10px] font-bold tracking-wide text-[var(--app-ink-soft)] uppercase"
          >
            {{ segment.timing }}
          </span>
          <div class="min-w-0">
            <p class="text-muted text-[11px] font-medium tracking-wide uppercase">{{ segment.context }}</p>
            <p class="mt-0.5 text-sm leading-relaxed text-[var(--app-ink)] italic">« {{ segment.text }} »</p>
          </div>
        </div>
        <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-4 py-3">
          <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
            <strong class="font-semibold text-[var(--app-ink)]">Conseils d'enregistrement :</strong> 1080p suffit (la 4K
            alourdit le fichier pour rien) · lumière face à vous · regardez l'objectif · souriez ·
            <strong class="font-semibold text-[var(--app-ink)]">ne nommez jamais une section précise du site</strong>
            (chaque site défile différemment — la voix doit rester valable pour tous).
          </p>
        </div>
      </div>
    </div>

    <UiLoader v-if="isLoading" />

    <template v-else>
      <!-- Clip actuel + réglages -->
      <div v-if="info?.has_video" class="card">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Votre clip</h2>
          <span class="app-badge app-badge--success font-semibold">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Prêt
          </span>
        </div>

        <div class="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
          <div class="space-y-3">
            <video
              v-if="previewUrl"
              :src="previewUrl"
              controls
              playsinline
              preload="metadata"
              class="aspect-video w-full rounded-xl border border-[var(--app-line)] bg-black"
            />
            <dl class="space-y-1.5 text-xs">
              <div class="flex justify-between gap-3">
                <dt class="text-muted">Fichier</dt>
                <dd class="truncate text-right text-[var(--app-ink)]">{{ info.original_filename }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-muted">Durée</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ Math.round(info.duration_seconds ?? 0) }} s</dd>
              </div>
              <div v-if="siteSegmentSeconds !== null" class="flex justify-between gap-3">
                <dt class="text-muted">Site du prospect à l'écran</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ siteSegmentSeconds }} s</dd>
              </div>
            </dl>
          </div>

          <form class="space-y-4" @submit.prevent="handleSaveSettings">
            <div>
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Découpage de la vidéo finale</h3>
              <p class="text-muted mt-1 text-xs leading-relaxed">
                Webcam plein écran au début (avec « Bonjour {Prénom} » en texte) et à la fin (votre appel à l'action) ;
                entre les deux, le site du prospect défile avec votre webcam en pastille.
              </p>
            </div>
            <div class="grid max-w-sm grid-cols-2 gap-3">
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

            <div class="flex items-center justify-between rounded-lg border border-[var(--app-line)] px-3 py-2.5">
              <div>
                <p class="text-sm font-medium text-[var(--app-ink)]">Génération automatique</p>
                <p class="text-muted text-xs">
                  Chaque nouveau site démo (manuel, en masse ou via l'automatisation) génère sa vidéo tout seul.
                </p>
              </div>
              <UiCheckbox id="video-auto-generate" v-model="autoGenerate" />
            </div>

            <div class="flex flex-wrap gap-2">
              <button type="submit" class="btn-primary" :disabled="isSavingSettings">
                <UIcon v-if="isSavingSettings" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
                {{ isSavingSettings ? 'Enregistrement…' : 'Enregistrer les réglages' }}
              </button>
              <button type="button" class="btn-secondary text-red-300" :disabled="isDeleting" @click="askDeleteClip">
                {{ isDeleting ? 'Suppression…' : 'Supprimer le clip' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Dropzone upload / remplacement -->
      <div class="card">
        <h2 class="mb-1 text-sm font-semibold text-[var(--app-ink)]">
          {{ info?.has_video ? 'Remplacer le clip' : 'Ajouter votre clip' }}
        </h2>
        <p class="text-muted mb-4 text-xs">MP4, WebM, MOV ou MKV — entre 12 et 90 secondes (cible : 30-45 s).</p>

        <div
          :class="[
            'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
            isDragging
              ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
              : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]',
          ]"
          role="button"
          tabindex="0"
          @click="openFilePicker"
          @keydown.enter.prevent="openFilePicker"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <UIcon
            :name="selectedFile ? 'i-lucide-file-video' : 'i-lucide-upload'"
            class="h-8 w-8 text-[var(--app-ink-soft)]"
          />
          <template v-if="selectedFile">
            <p class="text-sm font-medium text-[var(--app-ink)]">{{ selectedFile.name }}</p>
            <p class="text-muted text-xs">{{ formatFileSize(selectedFile.size) }} — cliquez pour changer de fichier</p>
          </template>
          <template v-else>
            <p class="text-sm font-medium text-[var(--app-ink)]">Glissez votre vidéo ici</p>
            <p class="text-muted text-xs">ou cliquez pour parcourir vos fichiers</p>
          </template>
          <input
            ref="fileInputRef"
            type="file"
            accept="video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv"
            class="hidden"
            @change="handleFileSelected"
          />
        </div>

        <button
          type="button"
          class="btn-primary mt-4 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!selectedFile || isUploading"
          @click="handleUpload"
        >
          <UIcon v-if="isUploading" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
          {{ isUploading ? 'Envoi en cours…' : 'Envoyer le clip' }}
        </button>
      </div>
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

/** Steps shown in the « Comment ça marche » card. */
const WORKFLOW_STEPS: Array<{ title: string; detail: string }> = [
  {
    title: 'Enregistrez votre clip webcam (une seule fois)',
    detail:
      'Webcam + micro, 30-45 s, speech générique — dépliez « Le speech recommandé » ci-dessous pour le texte prêt à lire.',
  },
  {
    title: 'Déposez le fichier ci-dessous',
    detail: "La durée est détectée automatiquement ; réglez l'intro et l'outro si besoin (4 s / 5 s par défaut).",
  },
  {
    title: 'Les vidéos se génèrent toutes seules',
    detail:
      "À chaque site démo créé (unitaire, en masse ou via l'automatisation), la vidéo personnalisée et sa vignette email sont produites en tâche de fond.",
  },
  {
    title: 'Insérez la vignette dans vos emails',
    detail:
      'Utilisez {vignette_video} dans vos modèles (2 modèles « ★ Vidéo » sont déjà prêts) — la file ignore les prospects dont la vidéo n’est pas prête.',
  },
]

/** Recommended generic speech, segment by segment (~30 s total). */
const SPEECH_SEGMENTS: Array<{ timing: string; context: string; text: string }> = [
  {
    timing: '0 - 4 s',
    context: 'Face caméra (plein écran)',
    text: "Bonjour ! Moi c'est Léo, développeur web.",
  },
  {
    timing: '4 - 27 s',
    context: 'Le site du prospect défile à l’écran, vous êtes en pastille',
    text:
      "Si je vous contacte, c'est que j'ai déjà créé un site web pour votre entreprise — vous êtes en train de le voir. " +
      'Il est en ligne, à votre nom, avec vos informations. Et surtout : vous pouvez tout modifier vous-même — ' +
      'textes, photos, horaires — sans développeur, depuis un espace d’administration très simple.',
  },
  {
    timing: '27 - 32 s',
    context: 'Face caméra (plein écran) — appel à l’action',
    text: 'Cliquez sur le lien juste en dessous pour le découvrir en vrai. À tout de suite !',
  },
]

const toast = useToast()

const info: Ref<PresenterVideoInfo | null> = ref<PresenterVideoInfo | null>(null)
const previewUrl: Ref<string | null> = ref<string | null>(null)
const isLoading: Ref<boolean> = ref<boolean>(true)
const isUploading: Ref<boolean> = ref<boolean>(false)
const isSavingSettings: Ref<boolean> = ref<boolean>(false)
const isDeleting: Ref<boolean> = ref<boolean>(false)
const isSpeechOpen: Ref<boolean> = ref<boolean>(false)
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
 * Format a file size in a human-readable French label.
 * @param bytes - Raw size in bytes.
 * @returns Formatted label (e.g. « 245 Mo »).
 */
function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${Math.round(bytes / (1024 * 1024))} Mo`
  return `${Math.max(1, Math.round(bytes / 1024))} Ko`
}

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
 * Open the hidden file input from the dropzone.
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
 * Accept a file dropped on the dropzone.
 * @param event - Native drop event.
 */
function handleDrop(event: DragEvent): void {
  isDragging.value = false
  const file: File | undefined = event.dataTransfer?.files?.[0]
  if (file) selectedFile.value = file
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
