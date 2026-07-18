<template>
  <Teleport to="body">
    <!-- Pas de backdrop : drawer non-modal (navigation possible pendant qu'il
         est ouvert), fermeture par X / Échap. -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--app-ink)] text-[var(--app-surface)]"
          >
            <UIcon name="i-lucide-video" class="h-5 w-5" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Vidéo de présentation</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              Votre clip webcam générique, réutilisé pour chaque vidéo de prospection
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <div class="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <UiCallout variant="info">
            Enregistrez <strong class="font-medium text-[var(--app-ink)]">une seule fois</strong> votre webcam
            (30-45&nbsp;s) avec un speech
            <strong class="font-medium text-[var(--app-ink)]">100&nbsp;% générique</strong> : « Bonjour, moi c'est Léo…
            voici votre site, vous pouvez tout modifier vous-même… ». Ne nommez
            <strong class="font-medium text-[var(--app-ink)]">jamais</strong> une section précise à un instant précis —
            la personnalisation passe par l'image (son site, son prénom), pas par la voix.
          </UiCallout>

          <UiLoader v-if="isLoading" />

          <template v-else>
            <!-- Clip actuel -->
            <div
              v-if="info?.has_video"
              class="space-y-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-4"
            >
              <div class="flex items-center justify-between gap-3">
                <h3 class="text-sm font-semibold text-[var(--app-ink)]">Clip actuel</h3>
                <span
                  class="rounded-full bg-[var(--app-green)]/20 px-2.5 py-0.5 text-[10px] font-bold text-[var(--app-green)] uppercase"
                >
                  Prêt
                </span>
              </div>
              <video
                v-if="previewUrl"
                :src="previewUrl"
                controls
                playsinline
                preload="metadata"
                class="aspect-video w-full rounded-lg border border-[var(--app-line)] bg-black"
              />
              <dl class="space-y-1.5 text-xs">
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--app-ink-soft)]">Fichier</dt>
                  <dd class="truncate text-right text-[var(--app-ink)]">{{ info.original_filename }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--app-ink-soft)]">Durée</dt>
                  <dd class="text-right text-[var(--app-ink)]">{{ formattedDuration }}</dd>
                </div>
                <div v-if="siteSegmentSeconds !== null" class="flex justify-between gap-3">
                  <dt class="text-[var(--app-ink-soft)]">Site à l'écran</dt>
                  <dd class="text-right text-[var(--app-ink)]">{{ siteSegmentSeconds }} s</dd>
                </div>
              </dl>
            </div>

            <!-- Réglages intro / outro -->
            <div v-if="info?.has_video" class="space-y-3">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Découpage de la vidéo finale</h3>
              <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Webcam plein écran au début (avec « Bonjour {Prénom} » en texte) et à la fin (votre appel à l'action) ;
                entre les deux, le site du prospect défile avec votre webcam en pastille.
              </p>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="text-muted mb-1.5 block text-xs font-medium" for="presenter-intro">Intro (s)</label>
                  <input
                    id="presenter-intro"
                    v-model.number="introSeconds"
                    type="number"
                    min="0"
                    max="30"
                    step="0.5"
                    class="input-field"
                  />
                </div>
                <div>
                  <label class="text-muted mb-1.5 block text-xs font-medium" for="presenter-outro">Outro (s)</label>
                  <input
                    id="presenter-outro"
                    v-model.number="outroSeconds"
                    type="number"
                    min="0"
                    max="30"
                    step="0.5"
                    class="input-field"
                  />
                </div>
              </div>
              <button
                type="button"
                class="btn-secondary w-full text-xs"
                :disabled="isSavingTimings"
                @click="handleSaveTimings"
              >
                {{ isSavingTimings ? 'Enregistrement…' : 'Enregistrer le découpage' }}
              </button>
            </div>

            <!-- Upload / remplacement -->
            <div class="space-y-3 border-t border-[var(--app-line)] pt-4">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">
                {{ info?.has_video ? 'Remplacer le clip' : 'Ajouter votre clip' }}
              </h3>
              <input
                ref="fileInputRef"
                type="file"
                accept="video/mp4,video/webm,video/quicktime,video/x-matroska"
                class="block w-full text-xs text-[var(--app-ink-soft)] file:mr-3 file:rounded-lg file:border file:border-[var(--app-line)] file:bg-[var(--app-surface-2)] file:px-3 file:py-2 file:text-xs file:font-medium file:text-[var(--app-ink)]"
                @change="handleFileSelected"
              />
              <p class="text-[11px] text-[var(--app-ink-soft)]">
                MP4, WebM, MOV ou MKV — entre 12 et 90 secondes (cible : 30-45 s).
              </p>
              <button
                type="button"
                class="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!selectedFile || isUploading"
                @click="handleUpload"
              >
                <UIcon v-if="isUploading" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
                {{ isUploading ? 'Envoi en cours…' : 'Envoyer le clip' }}
              </button>
            </div>

            <!-- Suppression -->
            <div v-if="info?.has_video" class="border-t border-[var(--app-line)] pt-4">
              <button
                type="button"
                class="btn-secondary w-full text-xs text-red-300"
                :disabled="isDeleting"
                @click="handleDelete"
              >
                {{ isDeleting ? 'Suppression…' : 'Supprimer le clip' }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { PresenterVideoInfo } from '~/services/presenterVideoService'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  deletePresenterVideo,
  getPresenterVideo,
  getPresenterVideoObjectUrl,
  updatePresenterVideoTimings,
  uploadPresenterVideo,
} from '~/services/presenterVideoService'
import { useToast } from '~/composables/useToast'

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

const toast = useToast()

const info: Ref<PresenterVideoInfo | null> = ref<PresenterVideoInfo | null>(null)
const previewUrl: Ref<string | null> = ref<string | null>(null)
const isLoading: Ref<boolean> = ref<boolean>(false)
const isUploading: Ref<boolean> = ref<boolean>(false)
const isSavingTimings: Ref<boolean> = ref<boolean>(false)
const isDeleting: Ref<boolean> = ref<boolean>(false)
const selectedFile: Ref<File | null> = ref<File | null>(null)
const fileInputRef: Ref<HTMLInputElement | null> = ref<HTMLInputElement | null>(null)
const introSeconds: Ref<number> = ref<number>(4)
const outroSeconds: Ref<number> = ref<number>(5)

/** Clip duration formatted as « 34 s ». */
const formattedDuration: ComputedRef<string> = computed((): string => {
  const seconds: number = info.value?.duration_seconds ?? 0
  return `${Math.round(seconds)} s`
})

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
 * Load the clip metadata + preview blob from the API.
 */
async function loadInfo(): Promise<void> {
  isLoading.value = true
  try {
    info.value = await getPresenterVideo()
    introSeconds.value = info.value.intro_seconds ?? 4
    outroSeconds.value = info.value.outro_seconds ?? 5
    releasePreview()
    if (info.value.has_video) {
      previewUrl.value = await getPresenterVideoObjectUrl()
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger le clip')
  } finally {
    isLoading.value = false
  }
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
 * Upload the selected clip (replaces the previous one server-side).
 */
async function handleUpload(): Promise<void> {
  if (!selectedFile.value) return
  isUploading.value = true
  try {
    info.value = await uploadPresenterVideo(selectedFile.value, introSeconds.value, outroSeconds.value)
    introSeconds.value = info.value.intro_seconds ?? introSeconds.value
    outroSeconds.value = info.value.outro_seconds ?? outroSeconds.value
    selectedFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    releasePreview()
    previewUrl.value = await getPresenterVideoObjectUrl()
    toast.success('Clip de présentation enregistré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi du clip")
  } finally {
    isUploading.value = false
  }
}

/**
 * Persist the intro/outro segments.
 */
async function handleSaveTimings(): Promise<void> {
  isSavingTimings.value = true
  try {
    info.value = await updatePresenterVideoTimings(introSeconds.value, outroSeconds.value)
    introSeconds.value = info.value.intro_seconds ?? introSeconds.value
    outroSeconds.value = info.value.outro_seconds ?? outroSeconds.value
    toast.success('Découpage enregistré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la mise à jour')
  } finally {
    isSavingTimings.value = false
  }
}

/**
 * Delete the clip after confirmation.
 */
async function handleDelete(): Promise<void> {
  if (!confirm('Supprimer votre clip de présentation ? Les vidéos déjà générées restent en ligne.')) return
  isDeleting.value = true
  try {
    info.value = await deletePresenterVideo()
    releasePreview()
    toast.success('Clip supprimé')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    isDeleting.value = false
  }
}

watch(
  () => props.open,
  (open: boolean): void => {
    if (open) void loadInfo()
    else releasePreview()
  },
  { immediate: true },
)

onBeforeUnmount((): void => {
  releasePreview()
})
</script>
